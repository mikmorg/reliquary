// THROWAWAY spike code (Reliquary A1-S3 follow-up): generates and checks the vectors for the
// DRAFT docs/spec/identifiers.md (kinds 0x01, 0x03, 0x04). Not production code.
use hkdf::Hkdf;
use hmac::{Hmac, KeyInit, Mac};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Read;

type HmacSha256 = Hmac<Sha256>;

const PREFIX: &str = "rd1-";
const B32: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";
const S0: &str = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";
const S1: &str = "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f";
const SROOT: &str = "404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f";

fn info_dedup(kind: u8, epoch: u16, scope: &str) -> String {
    format!("reliquary/v1/dedup-id-key/kind={:02x}/epoch={:04x}/scope={}", kind, epoch, scope)
}
fn info_root(scope: &str) -> String {
    format!("reliquary/v1/content-mac-key/scope={}", scope)
}
fn hkdf32(ikm: &[u8], info: &[u8]) -> [u8; 32] {
    let hk = Hkdf::<Sha256>::new(None, ikm); // salt absent = HashLen zero bytes (RFC 5869)
    let mut okm = [0u8; 32];
    hk.expand(info, &mut okm).unwrap();
    okm
}
fn hmac(key: &[u8], parts: &[&[u8]]) -> [u8; 32] {
    let mut m = <HmacSha256 as KeyInit>::new_from_slice(key).unwrap();
    for p in parts { m.update(p); }
    m.finalize().into_bytes().into()
}
fn b32(data: &[u8]) -> String {
    let mut out = String::new();
    let (mut acc, mut bits) = (0u32, 0u32);
    for &b in data {
        acc = (acc << 8) | b as u32; bits += 8;
        while bits >= 5 { bits -= 5; out.push(B32[((acc >> bits) & 31) as usize] as char); }
    }
    if bits > 0 { out.push(B32[((acc << (5 - bits)) & 31) as usize] as char); }
    out
}
fn b32_decode_strict(s: &str) -> Result<Vec<u8>, String> {
    if s.len() != 52 { return Err("body length".into()); }
    let (mut acc, mut bits, mut out) = (0u32, 0u32, Vec::new());
    for c in s.bytes() {
        let v = B32.iter().position(|&x| x == c).ok_or("body alphabet")? as u32;
        acc = (acc << 5) | v; bits += 5;
        if bits >= 8 { bits -= 8; out.push(((acc >> bits) & 0xff) as u8); }
    }
    if acc & ((1 << bits) - 1) != 0 { return Err("non-canonical trailing bits".into()); }
    Ok(out)
}
fn text(kind: u8, epoch: u16, mac: &[u8; 32]) -> String {
    format!("{}{:02x}-{:04x}-{}", PREFIX, kind, epoch, b32(mac))
}
fn binary(kind: u8, epoch: u16, mac: &[u8; 32]) -> Vec<u8> {
    let mut v = vec![kind]; v.extend_from_slice(&epoch.to_be_bytes()); v.extend_from_slice(mac); v
}
const KINDS_WHOLE_FILE: [u8; 3] = [0x01, 0x03, 0x04];
fn lhex(s: &str) -> bool { s.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c)) }
fn parse_text(s: &str) -> Result<(u8, u16, Vec<u8>), String> {
    if !s.is_ascii() { return Err("non-ascii".into()); }
    if s.len() != 64 { return Err(format!("length {}", s.len())); }
    if !s.starts_with(PREFIX) { return Err("prefix/version".into()); }
    let b = s.as_bytes();
    if b[6] != b'-' || b[11] != b'-' { return Err("separator".into()); }
    let (k, e, body) = (&s[4..6], &s[7..11], &s[12..]);
    if !lhex(k) { return Err("kind not lowercase hex".into()); }
    if !lhex(e) { return Err("epoch not lowercase hex".into()); }
    let kind = u8::from_str_radix(k, 16).unwrap();
    if kind == 0x02 { return Err("reserved kind".into()); }
    if !KINDS_WHOLE_FILE.contains(&kind) { return Err("unknown kind".into()); }
    let epoch = u16::from_str_radix(e, 16).unwrap();
    let mac = b32_decode_strict(body)?;
    Ok((kind, epoch, mac))
}
fn parse_binary(b: &[u8]) -> Result<(u8, u16, Vec<u8>), String> {
    if b.len() != 35 { return Err(format!("binary length {}", b.len())); }
    if b[0] == 0x02 { return Err("reserved kind".into()); }
    if !KINDS_WHOLE_FILE.contains(&b[0]) { return Err("unknown kind".into()); }
    Ok((b[0], u16::from_be_bytes([b[1], b[2]]), b[3..].to_vec()))
}

// content source: pattern i mod 251, or literal ascii
enum Content { Pattern(u64), Ascii(Vec<u8>) }
fn feed<F: FnMut(&[u8])>(c: &Content, mut f: F) {
    match c {
        Content::Ascii(v) => f(v),
        Content::Pattern(n) => {
            let period: Vec<u8> = (0..251u32).map(|i| i as u8).collect();
            let mut buf = Vec::with_capacity(251 * 4096);
            for _ in 0..4096 { buf.extend_from_slice(&period); }
            let mut left = *n;
            // irregular feed sizes to exercise streaming
            let sizes = [1usize, 7, 64, 1000, 65536, buf.len()];
            let mut i = 0usize; let mut off = 0usize;
            while left > 0 {
                let want = sizes[i % sizes.len()].min(left as usize);
                let start = off % 251;
                let take = want.min(buf.len() - start);
                f(&buf[start..start + take]);
                off += take; left -= take as u64; i += 1;
            }
        }
    }
}

struct Computed { sha256: [u8; 32], inner: [u8; 32], mac3: [u8; 32] }
fn compute(c: &Content, k3: &[u8; 32], kroot: &[u8; 32]) -> Computed {
    let mut sh = Sha256::new();
    let mut h3 = <HmacSha256 as KeyInit>::new_from_slice(k3).unwrap(); h3.update(&[0x03]);
    let mut hr = <HmacSha256 as KeyInit>::new_from_slice(kroot).unwrap();
    feed(c, |d| { sh.update(d); h3.update(d); hr.update(d); });
    Computed { sha256: sh.finalize().into(), mac3: h3.finalize().into_bytes().into(), inner: hr.finalize().into_bytes().into() }
}

fn gen() -> Value {
    let s0 = hex::decode(S0).unwrap(); let s1 = hex::decode(S1).unwrap(); let sroot = hex::decode(SROOT).unwrap();
    let kroot = hkdf32(&sroot, info_root("family").as_bytes());
    let mut vectors = Vec::new();
    let mut lengths: Vec<(String, Content)> = vec![("ascii:abc".into(), Content::Ascii(b"abc".to_vec()))];
    for n in [0u64, 1, 55, 56, 63, 64, 65, 1023, 1024, 1025, 65535, 65536, 65537, 1 << 20, (1u64 << 32) - 1, 1u64 << 32, (1u64 << 32) + 1] {
        lengths.push((format!("pattern-mod-251:{}", n), Content::Pattern(n)));
    }
    let mut epochs: Vec<(u16, &[u8], &str)> = vec![(0, &s0, "S_0")];
    let mut idx = 0;
    let small_extra: Vec<(u16, &[u8], &str)> = vec![(1, &s1, "S_1"), (0x0102, &s0, "S_0"), (0xffff, &s1, "S_1")];
    for (name, c) in lengths.iter() {
        let big = matches!(c, Content::Pattern(n) if *n >= (1u64 << 32) - 1);
        let mut eps = epochs.clone();
        if matches!(c, Content::Pattern(0)) || matches!(c, Content::Pattern(1025)) { eps.extend(small_extra.iter().cloned()); }
        for (e, s, sname) in eps {
            let k1 = hkdf32(s, info_dedup(1, e, "family").as_bytes());
            let k3 = hkdf32(s, info_dedup(3, e, "family").as_bytes());
            let k4 = hkdf32(s, info_dedup(4, e, "family").as_bytes());
            let cp = compute(c, &k3, &kroot);
            let mac1 = hmac(&k1, &[&[0x01], &cp.sha256]);
            let mac4 = hmac(&k4, &[&[0x04], &cp.inner]);
            for (kind, key, mac) in [(1u8, k1, mac1), (3u8, k3, cp.mac3), (4u8, k4, mac4)] {
                idx += 1;
                let mut v = json!({
                    "id": format!("P{:03}", idx), "kind": format!("{:02x}", kind), "epoch": e, "secret": sname,
                    "content": name, "large": big,
                    "sha256": hex::encode(cp.sha256),
                    "hkdf_info": info_dedup(kind, e, "family"),
                    "key": hex::encode(key),
                });
                if kind == 4 { v["inner"] = json!(hex::encode(cp.inner)); }
                v["mac"] = json!(hex::encode(mac));
                v["id_binary"] = json!(hex::encode(binary(kind, e, &mac)));
                v["id_text"] = json!(text(kind, e, &mac));
                vectors.push(v);
            }
        }
        epochs = vec![(0, &s0, "S_0")];
    }
    // domain-separation negatives over content pattern-mod-251:1025, epoch 0, S_0
    let c = Content::Pattern(1025);
    let k1 = hkdf32(&s0, info_dedup(1, 0, "family").as_bytes());
    let k3 = hkdf32(&s0, info_dedup(3, 0, "family").as_bytes());
    let k4 = hkdf32(&s0, info_dedup(4, 0, "family").as_bytes());
    let cp = compute(&c, &k3, &kroot);
    let d = cp.sha256;
    let mac1 = hmac(&k1, &[&[0x01], &d]);
    let mut contentbytes = Vec::new(); feed(&c, |x| contentbytes.extend_from_slice(x));
    let mac4 = hmac(&k4, &[&[0x04], &cp.inner]);
    let k1e1_same_secret = hkdf32(&s0, info_dedup(1, 1, "family").as_bytes());
    let neg = |id: &str, kind: u8, desc: &str, expected: [u8; 32], forbidden: Vec<u8>| json!({
        "id": id, "kind": format!("{:02x}", kind), "content": "pattern-mod-251:1025", "epoch": 0, "secret": "S_0",
        "mistake": desc, "expected_mac": hex::encode(expected), "forbidden": hex::encode(forbidden)});
    let mut negs = vec![
        neg("N01", 1, "kind byte 0x01 left out of the MAC input: HMAC(K, SHA-256(content))", mac1, hmac(&k1, &[&d]).to_vec()),
        neg("N02", 1, "family secret S_e used directly as the HMAC key (no HKDF)", mac1, hmac(&s0, &[&[0x01], &d]).to_vec()),
        neg("N03", 1, "HKDF info without the kind/epoch/scope suffix: exactly \"reliquary/v1/dedup-id-key\"", mac1, hmac(&hkdf32(&s0, b"reliquary/v1/dedup-id-key"), &[&[0x01], &d]).to_vec()),
        neg("N04", 1, "A1-S3 spike candidate b (info \"reliquary/v1/dedup-key/sha256-digest\", no kind byte); spike values must never match", mac1, hmac(&hkdf32(&s0, b"reliquary/v1/dedup-key/sha256-digest"), &[&d]).to_vec()),
        neg("N05", 1, "digest MACed as 64 hex characters instead of 32 raw bytes", mac1, hmac(&k1, &[&[0x01], hex::encode(d).as_bytes()]).to_vec()),
        neg("N06", 1, "epoch missing from key derivation: epoch-1 ID computed with the epoch-0 key under the same secret", hmac(&k1e1_same_secret, &[&[0x01], &d]), mac1.to_vec()),
        neg("N07", 1, "scope omitted from HKDF info", mac1, hmac(&hkdf32(&s0, b"reliquary/v1/dedup-id-key/kind=01/epoch=0000"), &[&[0x01], &d]).to_vec()),
        neg("N08", 1, "plain SHA-256 used as the ID", mac1, d.to_vec()),
        neg("N09", 3, "kind byte 0x03 left out: HMAC(K, content)", cp.mac3, hmac(&k3, &[&contentbytes]).to_vec()),
        neg("N10", 3, "kind-01 key used for kind 03", cp.mac3, hmac(&k1, &[&[0x03], &contentbytes]).to_vec()),
        neg("N11", 4, "inner MAC keyed with the epoch key instead of K_root", mac4, hmac(&k4, &[&[0x04], &hmac(&k4, &[&contentbytes])]).to_vec()),
        neg("N12", 4, "inner value is plain SHA-256 (confuses kind 04 with kind 01)", mac4, hmac(&k4, &[&[0x04], &d]).to_vec()),
        neg("N13", 4, "K_root used directly as the inner key without HKDF (S_root as key)", mac4, hmac(&k4, &[&[0x04], &hmac(&sroot, &[&contentbytes])]).to_vec()),
    ];
    // binary byte order negative
    let k1e = hkdf32(&s0, info_dedup(1, 0x0102, "family").as_bytes());
    let m = hmac(&k1e, &[&[0x01], &d]);
    let mut le = vec![1u8, 0x02, 0x01]; le.extend_from_slice(&m);
    negs.push(json!({"id": "N14", "kind": "01", "content": "pattern-mod-251:1025", "epoch": 0x0102, "secret": "S_0",
        "mistake": "epoch written little-endian in the binary form", "expected_binary": hex::encode(binary(1, 0x0102, &m)), "forbidden": hex::encode(le)}));
    // encoding negatives built from a valid ID
    let good = text(1, 0, &mac1);
    let body = &good[12..];
    let last_bad = { let mut s = good.clone(); s.pop(); let lc = body.as_bytes()[51];
        let alt = if lc == b'a' { 'b' } else if lc == b'q' { 'r' } else { 'a' }; s.push(alt); s };
    let enc: Vec<(&str, String, &str)> = vec![
        ("E01", good.to_uppercase(), "upper case"),
        ("E02", format!("{}{}{}", &good[..20], good[20..21].to_uppercase(), &good[21..]), "one upper-case body character"),
        ("E03", format!("{}{}{}", &good[..4], "01-00AB", &good[11..]), "upper-case hex in epoch"),
        ("E04", format!("{}====", good), "base32 padding"),
        ("E05", good[..63].to_string(), "body 51 characters"),
        ("E06", format!("{}a", good), "body 53 characters"),
        ("E07", last_bad, "non-canonical trailing bits"),
        ("E08", format!("{}1{}", &good[..30], &good[31..]), "character '1' outside the alphabet"),
        ("E09", format!("{}8{}", &good[..30], &good[31..]), "character '8' outside the alphabet"),
        ("E10", format!("rd2-{}", &good[4..]), "unknown text version rd2"),
        ("E11", format!("{}02{}", &good[..4], &good[6..]), "reserved kind 02 (chunk list) is not a whole-file ID"),
        ("E12", format!("{}ff{}", &good[..4], &good[6..]), "unknown kind ff"),
        ("E13", format!("{}000-{}", &good[..7], &good[12..]), "epoch with 3 digits"),
        ("E14", format!("{}00000-{}", &good[..7], &good[12..]), "epoch with 5 digits"),
        ("E15", hex::encode(d), "bare 64-hex string (a plain SHA-256) presented as an ID"),
        ("E16", format!("{}{}", &good[..12], hex::encode(mac1)), "hex body instead of base32"),
        ("E17", format!("{}\n", good), "trailing newline"),
        ("E18", format!("{}.", good), "trailing dot"),
        ("E19", format!(" {}", good), "leading space"),
        ("E20", good.replacen("-", "_", 1), "underscore separator"),
        ("E21", format!("{}{}", &good[..12], &good[12..].replace(&good[12..13], "=")), "'=' inside the body"),
    ];
    let mut encneg = Vec::new();
    for (id, s, why) in enc { encneg.push(json!({"id": id, "text": s, "reason": why})); }
    let bin_good = binary(1, 0, &mac1);
    let mut b34 = bin_good.clone(); b34.pop();
    let mut b36 = bin_good.clone(); b36.push(0);
    let mut b00 = bin_good.clone(); b00[0] = 0;
    let mut b02 = bin_good.clone(); b02[0] = 2;
    for (id, b, why) in [("B01", b34, "binary length 34"), ("B02", b36, "binary length 36"), ("B03", b00, "kind 0x00"), ("B04", b02, "reserved kind 0x02")] {
        encneg.push(json!({"id": id, "binary": hex::encode(b), "reason": why}));
    }
    json!({
        "title": "Reliquary identifiers.md DRAFT vectors (kinds 01, 03, 04; text form rd1). Not normative until ADR-0006 is accepted.",
        "spec": "docs/spec/identifiers.md (Draft)",
        "generated_by": "spikes/A1-S3/identifiers-v1/rust (sha2 0.11.0, hmac 0.13.0, hkdf 0.13.0)",
        "secrets": {"S_0": S0, "S_1": S1, "S_root": SROOT, "note": "test values only; never production"},
        "k_root": {"hkdf_info": info_root("family"), "key": hex::encode(kroot)},
        "content_rules": {"ascii:abc": "the 3 bytes 61 62 63", "pattern-mod-251:N": "N bytes; byte i is (i mod 251)"},
        "constructions": {
            "01": "mac = HMAC-SHA256(K, 0x01 || SHA-256(content))",
            "03": "mac = HMAC-SHA256(K, 0x03 || content)",
            "04": "inner = HMAC-SHA256(K_root, content); mac = HMAC-SHA256(K, 0x04 || inner)",
            "key": "K = HKDF-SHA256(ikm = S_e, salt = empty, info = ASCII 'reliquary/v1/dedup-id-key/kind=<kk>/epoch=<eeee>/scope=family', L = 32)"
        },
        "text_form": "rd1-<kind: 2 lowercase hex>-<epoch: 4 lowercase hex>-<mac: 52 chars RFC 4648 base32 alphabet, lower case, unpadded, last char's 4 unused bits zero>",
        "binary_form": "kind (1 byte) || epoch (u16 big-endian) || mac (32 bytes) = 35 bytes",
        "positive": vectors, "domain_separation_negative": negs, "encoding_negative": encneg
    })
}

fn verify(path: &str) -> i32 {
    let mut s = String::new(); std::fs::File::open(path).unwrap().read_to_string(&mut s).unwrap();
    let v: Value = serde_json::from_str(&s).unwrap();
    let regenerated = gen();
    let mut fails = 0;
    if regenerated != v { println!("FAIL: regenerated vectors differ from file"); fails += 1; }
    let (mut pos, mut rt) = (0, 0);
    for p in v["positive"].as_array().unwrap() {
        let t = p["id_text"].as_str().unwrap();
        match parse_text(t) { Ok((k, e, m)) => {
            let ok = format!("{:02x}", k) == p["kind"].as_str().unwrap() && e as u64 == p["epoch"].as_u64().unwrap() && hex::encode(&m) == p["mac"].as_str().unwrap()
                && binary(k, e, &m.clone().try_into().unwrap()) == hex::decode(p["id_binary"].as_str().unwrap()).unwrap()
                && parse_binary(&hex::decode(p["id_binary"].as_str().unwrap()).unwrap()).is_ok();
            if ok { rt += 1 } else { fails += 1; println!("FAIL roundtrip {}", p["id"]); } }
            Err(e) => { fails += 1; println!("FAIL parse {} {}", p["id"], e); } }
        pos += 1;
    }
    let mut en = 0;
    for e in v["encoding_negative"].as_array().unwrap() {
        let r = if let Some(t) = e["text"].as_str() { parse_text(t).map(|_| ()) } else { parse_binary(&hex::decode(e["binary"].as_str().unwrap()).unwrap()).map(|_| ()) };
        match r { Ok(_) => { fails += 1; println!("FAIL accepted {}", e["id"]); }, Err(why) => { en += 1; eprintln!("{} rejected: {}", e["id"].as_str().unwrap(), why); } }
    }
    let mut dn = 0;
    for n in v["domain_separation_negative"].as_array().unwrap() {
        let exp = n.get("expected_mac").or(n.get("expected_binary")).unwrap().as_str().unwrap();
        if exp == n["forbidden"].as_str().unwrap() { fails += 1; println!("FAIL negative collides {}", n["id"]); } else { dn += 1; }
    }
    println!("positive parsed+roundtrip {}/{}; encoding negatives rejected {}/{}; domain negatives distinct {}/{}; regenerate-equal {}",
        rt, pos, en, v["encoding_negative"].as_array().unwrap().len(), dn, v["domain_separation_negative"].as_array().unwrap().len(), fails == 0);
    if fails == 0 { 0 } else { 1 }
}

fn wycheproof(hmac_path: &str, hkdf_path: &str, go_path: &str) -> i32 {
    let mut fails = 0; let (mut n_h, mut n_k, mut n_g) = (0, 0, 0);
    let h: Value = serde_json::from_str(&std::fs::read_to_string(hmac_path).unwrap()).unwrap();
    for g in h["testGroups"].as_array().unwrap() { for t in g["tests"].as_array().unwrap() {
        let key = hex::decode(t["key"].as_str().unwrap()).unwrap(); let msg = hex::decode(t["msg"].as_str().unwrap()).unwrap();
        let tag = hex::decode(t["tag"].as_str().unwrap()).unwrap();
        let full = hmac(&key, &[&msg]);
        let matches = full[..tag.len()] == tag[..];
        let valid = t["result"] == "valid";
        if matches != valid { fails += 1; println!("FAIL wycheproof hmac tc {}", t["tcId"]); }
        n_h += 1; } }
    let k: Value = serde_json::from_str(&std::fs::read_to_string(hkdf_path).unwrap()).unwrap();
    for g in k["testGroups"].as_array().unwrap() { for t in g["tests"].as_array().unwrap() {
        let ikm = hex::decode(t["ikm"].as_str().unwrap()).unwrap(); let salt = hex::decode(t["salt"].as_str().unwrap()).unwrap();
        let info = hex::decode(t["info"].as_str().unwrap()).unwrap(); let size = t["size"].as_u64().unwrap() as usize;
        let hk = Hkdf::<Sha256>::new(Some(&salt), &ikm); let mut out = vec![0u8; size];
        let r = hk.expand(&info, &mut out);
        let got_ok = r.is_ok() && hex::encode(&out) == t["okm"].as_str().unwrap();
        let valid = t["result"] == "valid";
        if got_ok != valid { fails += 1; println!("FAIL wycheproof hkdf tc {}", t["tcId"]); }
        n_k += 1; } }
    let go: Value = serde_json::from_str(&std::fs::read_to_string(go_path).unwrap()).unwrap();
    for t in go["vectors"].as_array().unwrap() {
        let ikm = hex::decode(t["ikm"].as_str().unwrap()).unwrap(); let salt = hex::decode(t["salt"].as_str().unwrap()).unwrap();
        let hk = if t["salt_nil"].as_bool().unwrap() { Hkdf::<Sha256>::new(None, &ikm) } else { Hkdf::<Sha256>::new(Some(&salt), &ikm) };
        let okm_exp = hex::decode(t["okm"].as_str().unwrap()).unwrap(); let mut out = vec![0u8; okm_exp.len()];
        hk.expand(&hex::decode(t["info"].as_str().unwrap()).unwrap(), &mut out).unwrap();
        let (prk, _) = Hkdf::<Sha256>::extract(if t["salt_nil"].as_bool().unwrap() { None } else { Some(&salt) }, &ikm);
        if out != okm_exp || hex::encode(prk) != t["prk"].as_str().unwrap() { fails += 1; println!("FAIL go hkdf"); }
        n_g += 1; }
    println!("wycheproof hmac {} cases, hkdf {} cases, go/rfc5869 hkdf {} cases, failures {}", n_h, n_k, n_g, fails);
    if fails == 0 { 0 } else { 1 }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    match a.get(1).map(|s| s.as_str()) {
        Some("gen") => println!("{}", serde_json::to_string_pretty(&gen()).unwrap()),
        Some("verify") => std::process::exit(verify(&a[2])),
        Some("wycheproof") => std::process::exit(wycheproof(&a[2], &a[3], &a[4])),
        _ => { eprintln!("usage: gen | verify FILE | wycheproof HMAC.json HKDF.json GO.json"); std::process::exit(2) }
    }
}
