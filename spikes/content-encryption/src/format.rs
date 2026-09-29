//! THROWAWAY SPIKE CODE. Not production.
//!
//! Reliquary content object = a *standard* age v1 file with exactly one X25519
//! recipient stanza, produced by our own encoder so that the per-upload payload
//! key, header and payload nonce can be persisted and any byte range of the
//! object can be regenerated deterministically.
//!
//! Object layout (byte offsets, prefix_len = 184 for one X25519 stanza):
//!   [0, 168)                          age header (fixed shape, see `new_header`)
//!   [168, 184)                        16-byte payload nonce
//!   [prefix_len + c*65552, ...)       STREAM chunk c: ChaCha20-Poly1305(64 KiB pt) || 16-byte tag
//!
//! Multipart layout: part size P = k * 65552 (k chunks per part). Because the
//! prefix shifts the payload, every part boundary after part 0 lands at the
//! same offset inside a chunk; the boundary chunk is encrypted once (cached)
//! or twice (deterministic) and sliced. `prefix_len` is a layout field so a
//! future header with more stanzas (e.g. ML-KEM hybrid) only changes data.

use base64::{engine::general_purpose::STANDARD_NO_PAD as B64, Engine};
use chacha20poly1305::{
    aead::{Aead, AeadInOut, KeyInit},
    ChaCha20Poly1305, Key, Nonce,
};
use hkdf::Hkdf;
use hmac::{Hmac, Mac};
use rand::{rngs::OsRng, RngCore};
use sha2::{Digest, Sha256};
use x25519_dalek::{PublicKey, StaticSecret};
use zeroize::Zeroize;

pub const CHUNK_PT: u64 = 64 * 1024;
pub const TAG: u64 = 16;
pub const CHUNK_CT: u64 = CHUNK_PT + TAG; // 65552
pub const HEADER_LEN_X25519: u64 = 168;
pub const NONCE_LEN: u64 = 16;
pub const PREFIX_LEN_X25519: u64 = HEADER_LEN_X25519 + NONCE_LEN; // 184
pub const R2_MIN_PART: u64 = 5 * 1024 * 1024;
pub const R2_MAX_PART: u64 = 5 * 1024 * 1024 * 1024;
pub const R2_MAX_PARTS: u64 = 10_000;
/// 80 chunks = 5,244,160 bytes per part: the smallest whole number of chunks
/// that is >= R2's 5 MiB minimum part size.
pub const BASE_CHUNKS_PER_PART: u64 = 80;

pub fn hkdf_into(salt: &[u8], info: &[u8], ikm: &[u8], out: &mut [u8]) {
    Hkdf::<Sha256>::new(Some(salt), ikm).expand(info, out).expect("valid HKDF length");
}

pub fn hkdf32(salt: &[u8], info: &[u8], ikm: &[u8]) -> [u8; 32] {
    let mut okm = [0u8; 32];
    hkdf_into(salt, info, ikm, &mut okm);
    okm
}

pub fn hmac_sha256(key: &[u8], parts: &[&[u8]]) -> [u8; 32] {
    let mut m = <Hmac<Sha256> as KeyInit>::new_from_slice(key).unwrap();
    for p in parts {
        m.update(p);
    }
    m.finalize().into_bytes().into()
}

pub fn sha256(data: &[u8]) -> [u8; 32] {
    Sha256::digest(data).into()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Layout {
    pub pt_len: u64,
    pub chunks_per_part: u64,
    pub prefix_len: u64,
}

impl Layout {
    /// Production part-size policy: smallest k = 80 * 2^j such that the object
    /// fits in <= 10,000 parts. Part size P = k * 65552 is >= 5 MiB and must be
    /// <= 5 GiB (k <= 40,960, so objects up to ~26.8 TB).
    pub fn policy(pt_len: u64, prefix_len: u64) -> Result<Layout, String> {
        let mut k = BASE_CHUNKS_PER_PART;
        loop {
            let l = Layout { pt_len, chunks_per_part: k, prefix_len };
            if l.part_size() > R2_MAX_PART {
                return Err("file too large for R2 multipart (> ~26.8 TB)".into());
            }
            debug_assert!(l.part_size() >= R2_MIN_PART);
            if l.num_parts() <= R2_MAX_PARTS {
                return Ok(l);
            }
            k *= 2;
        }
    }
    pub fn n_chunks(&self) -> u64 {
        std::cmp::max(1, self.pt_len.div_ceil(CHUNK_PT))
    }
    pub fn ct_len(&self) -> u64 {
        self.prefix_len + self.pt_len + TAG * self.n_chunks()
    }
    pub fn part_size(&self) -> u64 {
        self.chunks_per_part * CHUNK_CT
    }
    pub fn num_parts(&self) -> u64 {
        self.ct_len().div_ceil(self.part_size())
    }
    /// Half-open object byte range of part p (0-based; wire part number = p + 1).
    pub fn part_range(&self, p: u64) -> (u64, u64) {
        let ps = self.part_size();
        (p * ps, std::cmp::min((p + 1) * ps, self.ct_len()))
    }
    pub fn chunk_pt_range(&self, c: u64) -> (u64, u64) {
        (c * CHUNK_PT, std::cmp::min((c + 1) * CHUNK_PT, self.pt_len))
    }
    pub fn chunk_obj_range(&self, c: u64) -> (u64, u64) {
        let (a, b) = self.chunk_pt_range(c);
        let s = self.prefix_len + c * CHUNK_CT;
        (s, s + (b - a) + TAG)
    }
    /// Inclusive range of chunks whose ciphertext overlaps object bytes [s, e).
    pub fn chunks_in_range(&self, s: u64, e: u64) -> Option<(u64, u64)> {
        if e <= self.prefix_len || e <= s {
            return None;
        }
        let first = if s < self.prefix_len { 0 } else { (s - self.prefix_len) / CHUNK_CT };
        let last = (e - 1 - self.prefix_len) / CHUNK_CT;
        Some((first, last))
    }
    #[allow(dead_code)]
    /// Inclusive range of parts that chunk c's ciphertext overlaps.
    pub fn parts_of_chunk(&self, c: u64) -> (u64, u64) {
        let (s, e) = self.chunk_obj_range(c);
        (s / self.part_size(), (e - 1) / self.part_size())
    }
    /// Plaintext length implied by an object length, rejecting impossible
    /// lengths (a body of 0 bytes, a final chunk of 1..=15 bytes, or an empty
    /// final chunk after a full chunk).
    pub fn pt_len_from_ct_len(ct_len: u64, prefix_len: u64) -> Result<u64, String> {
        if ct_len < prefix_len + TAG {
            return Err(format!("object length {ct_len} too short"));
        }
        let body = ct_len - prefix_len;
        let full = body / CHUNK_CT;
        let rem = body % CHUNK_CT;
        let n = match rem {
            0 => full,
            1..=15 => return Err(format!("invalid object length {ct_len}: final chunk shorter than a tag")),
            16 if full > 0 => return Err(format!("invalid object length {ct_len}: empty final chunk after a full chunk")),
            _ => full + 1,
        };
        Ok(body - n * TAG)
    }
}

/// The 12-byte STREAM nonce: 11-byte big-endian counter || last flag.
pub fn chunk_nonce(c: u64, last: bool) -> [u8; 12] {
    let mut n = [0u8; 12];
    n[3..11].copy_from_slice(&c.to_be_bytes());
    n[11] = last as u8;
    n
}

pub struct PayloadCipher {
    aead: ChaCha20Poly1305,
    n_chunks: u64,
}

impl PayloadCipher {
    pub fn new(payload_key: &[u8; 32], n_chunks: u64) -> Self {
        PayloadCipher { aead: ChaCha20Poly1305::new(&Key::from(*payload_key)), n_chunks }
    }
    /// Encrypts chunk c in place (appends the 16-byte tag).
    pub fn encrypt_chunk(&self, c: u64, buf: &mut Vec<u8>) {
        let n = chunk_nonce(c, c + 1 == self.n_chunks);
        self.aead.encrypt_in_place(&Nonce::from(n), b"", buf).expect("chunk encryption");
    }
    pub fn decrypt_chunk(&self, c: u64, buf: &mut Vec<u8>) -> Result<(), String> {
        let n = chunk_nonce(c, c + 1 == self.n_chunks);
        self.aead
            .decrypt_in_place(&Nonce::from(n), b"", buf)
            .map_err(|_| format!("chunk {c}: authentication failed"))
    }
}

/// Generates a fresh age v1 header (single X25519 stanza) + payload nonce.
/// Returns (prefix[184], payload_key). The file key never leaves this function.
///
/// Randomness is *hedged*: one 32-byte CSPRNG seed is expanded with HKDF using
/// `context` (the plaintext SHA-256) as salt into the file key, the ephemeral
/// X25519 secret and the payload nonce. With a healthy RNG this is exactly as
/// random as drawing them directly (the spec's CSPRNG requirement holds). If
/// the RNG ever repeats (VM snapshot/clone), two *different* plaintexts still
/// get different keys, so a repeated seed can never cause keystream reuse.
pub fn new_header(recipient: &[u8; 32], context: &[u8; 32]) -> (Vec<u8>, [u8; 32]) {
    let mut seed = [0u8; 32];
    OsRng.fill_bytes(&mut seed);
    let mut file_key = [0u8; 16];
    hkdf_into(context, b"reliquary/v1/hedge/file-key", &seed, &mut file_key);
    let mut esk_bytes = hkdf32(context, b"reliquary/v1/hedge/x25519-ephemeral", &seed);
    let mut nonce = [0u8; 16];
    hkdf_into(context, b"reliquary/v1/hedge/payload-nonce", &seed, &mut nonce);
    seed.zeroize();

    let esk = StaticSecret::from(esk_bytes);
    esk_bytes.zeroize();
    let epk = PublicKey::from(&esk);
    let shared = esk.diffie_hellman(&PublicKey::from(*recipient));
    assert!(shared.was_contributory(), "non-contributory X25519 (low-order recipient?)");
    let mut salt = [0u8; 64];
    salt[..32].copy_from_slice(epk.as_bytes());
    salt[32..].copy_from_slice(recipient);
    let mut wrap_key = hkdf32(&salt, b"age-encryption.org/v1/X25519", shared.as_bytes());
    let body = ChaCha20Poly1305::new(&Key::from(wrap_key))
        .encrypt(&Nonce::default(), &file_key[..])
        .expect("wrap");
    wrap_key.zeroize();

    let mut header = format!(
        "age-encryption.org/v1\n-> X25519 {}\n{}\n---",
        B64.encode(epk.as_bytes()),
        B64.encode(&body)
    );
    let mut mac_key = hkdf32(&[], b"header", &file_key);
    let mac = hmac_sha256(&mac_key, &[header.as_bytes()]);
    mac_key.zeroize();
    header.push(' ');
    header.push_str(&B64.encode(mac));
    header.push('\n');
    assert_eq!(header.len() as u64, HEADER_LEN_X25519);

    let payload_key = hkdf32(&nonce, b"payload", &file_key);
    file_key.zeroize();

    let mut prefix = header.into_bytes();
    prefix.extend_from_slice(&nonce);
    (prefix, payload_key)
}

/// The base64 header MAC of a prefix produced by `new_header` (binds a
/// metadata record to one encrypted instance).
pub fn header_mac_b64(prefix: &[u8]) -> Result<String, String> {
    let hdr = std::str::from_utf8(&prefix[..HEADER_LEN_X25519 as usize]).map_err(|_| "header not utf8")?;
    Ok(hdr.rsplit("--- ").next().ok_or("no mac line")?.trim_end().to_string())
}

/// Homelab side: parse our fixed-shape header, unwrap the file key with the
/// X25519 identity, verify the header MAC and return the payload key.
/// (Any general age implementation can do this; this is the reference path
/// for range reads.)
pub fn open_prefix(prefix: &[u8], identity: &[u8; 32]) -> Result<[u8; 32], String> {
    if prefix.len() < PREFIX_LEN_X25519 as usize {
        return Err("short prefix".into());
    }
    let hdr = std::str::from_utf8(&prefix[..HEADER_LEN_X25519 as usize]).map_err(|_| "header not utf8")?;
    let lines: Vec<&str> = hdr.split('\n').collect();
    if lines.len() != 5
        || lines[0] != "age-encryption.org/v1"
        || !lines[1].starts_with("-> X25519 ")
        || !lines[3].starts_with("--- ")
        || !lines[4].is_empty()
    {
        return Err("unexpected header shape".into());
    }
    let epk: [u8; 32] = B64.decode(&lines[1][10..]).map_err(|_| "epk b64")?.try_into().map_err(|_| "epk len")?;
    let body = B64.decode(lines[2]).map_err(|_| "body b64")?;
    if body.len() != 32 {
        return Err("body len".into());
    }
    let mac_given = B64.decode(&lines[3][4..]).map_err(|_| "mac b64")?;
    let sk = StaticSecret::from(*identity);
    let pk = PublicKey::from(&sk);
    let shared = sk.diffie_hellman(&PublicKey::from(epk));
    if !shared.was_contributory() {
        return Err("all-zero shared secret".into());
    }
    let mut salt = [0u8; 64];
    salt[..32].copy_from_slice(&epk);
    salt[32..].copy_from_slice(pk.as_bytes());
    let wrap_key = hkdf32(&salt, b"age-encryption.org/v1/X25519", shared.as_bytes());
    let fk = ChaCha20Poly1305::new(&Key::from(wrap_key))
        .decrypt(&Nonce::default(), body.as_slice())
        .map_err(|_| "stanza unwrap failed")?;
    let mac_key = hkdf32(&[], b"header", &fk);
    let mac_end = hdr.find("\n---").unwrap() + 4;
    let mut mac = <Hmac<Sha256> as KeyInit>::new_from_slice(&mac_key).unwrap();
    mac.update(&prefix[..mac_end]);
    mac.verify_slice(&mac_given).map_err(|_| "header MAC mismatch")?;
    let nonce = &prefix[HEADER_LEN_X25519 as usize..PREFIX_LEN_X25519 as usize];
    Ok(hkdf32(nonce, b"payload", &fk))
}

/// Encrypts a small in-memory buffer as a complete age file (used for the
/// metadata record, which never needs resumption).
pub fn encrypt_small(recipient: &[u8; 32], data: &[u8]) -> Vec<u8> {
    let layout = Layout { pt_len: data.len() as u64, chunks_per_part: 1, prefix_len: PREFIX_LEN_X25519 };
    let (mut out, mut pk) = new_header(recipient, &sha256(data));
    let cipher = PayloadCipher::new(&pk, layout.n_chunks());
    pk.zeroize();
    for c in 0..layout.n_chunks() {
        let (a, b) = layout.chunk_pt_range(c);
        let mut buf = data[a as usize..b as usize].to_vec();
        cipher.encrypt_chunk(c, &mut buf);
        out.extend_from_slice(&buf);
    }
    out
}

/// Strict parser for an age X25519 recipient: lowercase, canonical Bech32
/// (not Bech32m), HRP "age", 32 bytes.
pub fn parse_recipient(s: &str) -> Result<[u8; 32], String> {
    use bech32::{FromBase32, ToBase32, Variant};
    let s = s.trim();
    if s.bytes().any(|b| b.is_ascii_uppercase()) {
        return Err("recipient must be lowercase".into());
    }
    let (hrp, data, variant) = bech32::decode(s).map_err(|e| e.to_string())?;
    if variant != Variant::Bech32 {
        return Err("recipient must use Bech32, not Bech32m".into());
    }
    if hrp != "age" {
        return Err(format!("unexpected hrp {hrp}"));
    }
    let key: [u8; 32] = Vec::<u8>::from_base32(&data).map_err(|e| e.to_string())?.try_into().map_err(|_| "recipient length".to_string())?;
    if bech32::encode("age", key.to_base32(), Variant::Bech32).map_err(|e| e.to_string())? != s {
        return Err("non-canonical recipient encoding".into());
    }
    Ok(key)
}

pub fn parse_identity_file(text: &str) -> Result<[u8; 32], String> {
    use bech32::{FromBase32, Variant};
    let line = text.lines().find(|l| l.starts_with("AGE-SECRET-KEY-1")).ok_or("no identity")?;
    let (hrp, data, variant) = bech32::decode(line.trim()).map_err(|e| e.to_string())?;
    if hrp != "age-secret-key-" || variant != Variant::Bech32 {
        return Err(format!("unexpected identity encoding (hrp {hrp})"));
    }
    Vec::<u8>::from_base32(&data).map_err(|e| e.to_string())?.try_into().map_err(|_| "len".to_string())
}

/// What a device pins at enrollment. The QR code / USB kit carries
/// SHA-256(bundle file bytes); the device refuses a bundle that does not match.
#[derive(serde::Serialize, serde::Deserialize)]
pub struct TrustBundle {
    pub v: u32,
    /// age X25519 recipient of the homelab (content + metadata encryption).
    pub recipient: String,
    /// Base64 Ed25519 public key that signs commit receipts.
    pub receipt_key: String,
}

pub struct Trust {
    pub recipient: [u8; 32],
    pub receipt_key: ed25519_dalek::VerifyingKey,
}

pub fn load_trust(bytes: &[u8], pin_hex: &str) -> Result<Trust, String> {
    let got = hex::encode(sha256(bytes));
    if !pin_hex.eq_ignore_ascii_case(&got) {
        return Err(format!("trust bundle does not match pinned fingerprint (got {got})"));
    }
    let tb: TrustBundle = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
    if tb.v != 1 {
        return Err("unsupported trust bundle version".into());
    }
    let recipient = parse_recipient(&tb.recipient)?;
    let rk: [u8; 32] = base64::engine::general_purpose::STANDARD
        .decode(&tb.receipt_key)
        .map_err(|e| e.to_string())?
        .try_into()
        .map_err(|_| "receipt key length".to_string())?;
    let receipt_key = ed25519_dalek::VerifyingKey::from_bytes(&rk).map_err(|e| e.to_string())?;
    Ok(Trust { recipient, receipt_key })
}

/// Dedup key derived from the family secret (domain separation + versioning).
/// dedup_id = HMAC-SHA256(dedup_key, plaintext).
pub fn dedup_key(family_secret: &[u8]) -> [u8; 32] {
    hkdf32(&[], b"reliquary/v1/dedup-key", family_secret)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Chunk/part mapping must hold for any prefix length (future multi-stanza
    /// headers) and any k: every part except the last has the same size, parts
    /// tile the object, and chunks_in_range/parts_of_chunk agree.
    #[test]
    fn layout_math_any_prefix() {
        let prefixes = [1u64, 16, 184, 200, 1000, 1234, 65_551];
        let sizes = [0u64, 1, 65_535, 65_536, 65_537, 3 * 65_536 + 5, 1_000_000];
        for &pl in &prefixes {
            for &k in &[1u64, 2, 3, 7] {
                for &n in &sizes {
                    let l = Layout { pt_len: n, chunks_per_part: k, prefix_len: pl };
                    let np = l.num_parts();
                    let mut cursor = 0;
                    for p in 0..np {
                        let (s, e) = l.part_range(p);
                        assert_eq!(s, cursor);
                        if p + 1 < np {
                            assert_eq!(e - s, l.part_size());
                        }
                        cursor = e;
                        if let Some((c0, c1)) = l.chunks_in_range(s, e) {
                            for c in c0..=c1 {
                                let (lo, hi) = l.parts_of_chunk(c);
                                assert!(lo <= p && p <= hi);
                            }
                            if p > 0 && pl < CHUNK_CT && p * k >= 1 && p * k - 1 < l.n_chunks() {
                                assert_eq!(c0, p * k - 1, "part p>=1 starts in chunk p*k-1");
                            }
                        }
                    }
                    assert_eq!(cursor, l.ct_len());
                    assert_eq!(Layout::pt_len_from_ct_len(l.ct_len(), pl).unwrap(), n);
                }
            }
        }
    }

    #[test]
    fn invalid_lengths_rejected() {
        let p = PREFIX_LEN_X25519;
        assert!(Layout::pt_len_from_ct_len(p, p).is_err());
        assert!(Layout::pt_len_from_ct_len(p + 15, p).is_err());
        assert_eq!(Layout::pt_len_from_ct_len(p + 16, p).unwrap(), 0);
        assert!(Layout::pt_len_from_ct_len(p + CHUNK_CT + 1, p).is_err());
        assert!(Layout::pt_len_from_ct_len(p + CHUNK_CT + 16, p).is_err());
        assert_eq!(Layout::pt_len_from_ct_len(p + CHUNK_CT + 17, p).unwrap(), CHUNK_PT + 1);
    }

    #[test]
    fn policy_limits() {
        let l = Layout::policy(0, 184).unwrap();
        assert_eq!(l.part_size(), 5_244_160);
        assert!(l.part_size() >= R2_MIN_PART);
        // largest object at k = 80: 10,000 parts
        let max80 = 10_000 * 5_244_160 - 184 - 16 * ((10_000 * 5_244_160u64).div_ceil(CHUNK_CT));
        assert_eq!(Layout::policy(max80, 184).unwrap().chunks_per_part, 80);
        assert_eq!(Layout::policy(max80 + 65_536, 184).unwrap().chunks_per_part, 160);
        assert!(Layout::policy(30_000_000_000_000, 184).is_err());
        assert_eq!(Layout::policy(26_000_000_000_000, 184).unwrap().chunks_per_part, 40_960);
    }

    #[test]
    fn recipient_strict() {
        let sk = StaticSecret::from([7u8; 32]);
        let pk = PublicKey::from(&sk);
        use bech32::ToBase32;
        let good = bech32::encode("age", pk.as_bytes().to_base32(), bech32::Variant::Bech32).unwrap();
        assert!(parse_recipient(&good).is_ok());
        assert!(parse_recipient(&good.to_ascii_uppercase()).is_err());
        let m = bech32::encode("age", pk.as_bytes().to_base32(), bech32::Variant::Bech32m).unwrap();
        assert!(parse_recipient(&m).is_err());
    }
}
