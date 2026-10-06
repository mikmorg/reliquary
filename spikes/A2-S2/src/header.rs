//! THROWAWAY SPIKE CODE. Not production.
//!
//! age v1 header: a multi-stanza encoder and a strict generic decoder for the
//! two public-key recipient types Reliquary may use:
//!   * `X25519`          (classic; age v1 since 2019)
//!   * `mlkem768x25519`  (hybrid PQ, X-Wing via HPKE SealBase; C2SP age spec)
//!
//! The stanza construction for mlkem768x25519 follows the C2SP age spec:
//!   HPKE SealBase, KEM MLKEM768-X25519 (0x647a), KDF HKDF-SHA256,
//!   AEAD ChaCha20Poly1305, info "age-encryption.org/mlkem768x25519", aad "".
//!   Stanza: "-> mlkem768x25519 <b64(enc, 1120 B)>" + body = 32-byte ct.
//! It is implemented with the Rust `hpke` 0.14.1 crate. Whether that matches Go
//! age byte for byte is exactly what spike A2-S3 tests.
//!
//! Randomness is hedged like CE spike 2: one CSPRNG seed is expanded with HKDF
//! (salt = context, normally SHA-256 of the plaintext) into the file key, the
//! payload nonce and each stanza's randomness (X25519 ephemeral scalar, or the
//! 64 bytes of X-Wing encapsulation randomness, fed through `HedgeRng`).

use crate::format::{hkdf32, hkdf_into, hmac_sha256};
use base64::{engine::general_purpose::STANDARD_NO_PAD as B64, Engine};
use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Key, Nonce,
};
use hmac::{Hmac, Mac};
use hpke::{kem::XWing, Deserializable, Kem as KemTrait, OpModeR, OpModeS, Serializable};
use rand::{rngs::OsRng, RngCore};
use sha2::Sha256;
use x25519_dalek::{PublicKey, StaticSecret};
use zeroize::Zeroize;

pub type XPk = <XWing as KemTrait>::PublicKey;
pub type XSk = <XWing as KemTrait>::PrivateKey;
pub type XEnc = <XWing as KemTrait>::EncappedKey;
type HAead = hpke::aead::ChaCha20Poly1305;
type HKdf = hpke::kdf::HkdfSha256;

pub const PQ_TYPE: &str = "mlkem768x25519";
pub const PQ_LABEL: &[u8] = b"age-encryption.org/mlkem768x25519";
pub const X25519_LABEL: &[u8] = b"age-encryption.org/v1/X25519";
pub const VERSION_LINE: &str = "age-encryption.org/v1";
pub const XWING_ENC_LEN: usize = 1120;
pub const XWING_PK_LEN: usize = 1216;
pub const XWING_ENCAP_RAND: usize = 64;
/// Strict decoder limits (spec parameters for object-format.md, not budgets).
pub const MAX_HEADER_LEN: usize = 16 * 1024;
pub const MAX_STANZAS: usize = 16;

// ------------------------------------------------------------ keys

pub enum Recipient {
    X25519([u8; 32]),
    Pq(Box<XPk>),
}

impl Recipient {
    pub fn is_pq(&self) -> bool {
        matches!(self, Recipient::Pq(_))
    }
    /// Strict parser: lowercase, canonical Bech32 (not Bech32m), HRP "age"
    /// (32 bytes) or "age1pq" (1216 bytes, valid X-Wing encapsulation key).
    pub fn parse(s: &str) -> Result<Recipient, String> {
        use bech32::{FromBase32, ToBase32, Variant};
        let s = s.trim();
        if s.bytes().any(|b| b.is_ascii_uppercase()) {
            return Err("recipient must be lowercase".into());
        }
        let (hrp, data, variant) = bech32::decode(s).map_err(|e| e.to_string())?;
        if variant != Variant::Bech32 {
            return Err("recipient must use Bech32, not Bech32m".into());
        }
        let raw = Vec::<u8>::from_base32(&data).map_err(|e| e.to_string())?;
        if bech32::encode(&hrp, raw.to_base32(), Variant::Bech32).map_err(|e| e.to_string())? != s {
            return Err("non-canonical recipient encoding".into());
        }
        match hrp.as_str() {
            "age" => Ok(Recipient::X25519(raw.try_into().map_err(|_| "X25519 recipient length")?)),
            "age1pq" => {
                if raw.len() != XWING_PK_LEN {
                    return Err(format!("PQ recipient length {}", raw.len()));
                }
                Ok(Recipient::Pq(Box::new(XPk::from_bytes(&raw).map_err(|e| format!("invalid X-Wing key: {e}"))?)))
            }
            h => Err(format!("unexpected recipient type {h}")),
        }
    }
    pub fn encode(&self) -> String {
        use bech32::{ToBase32, Variant};
        match self {
            Recipient::X25519(k) => bech32::encode("age", k.to_base32(), Variant::Bech32).unwrap(),
            Recipient::Pq(pk) => bech32::encode("age1pq", pk.to_bytes().to_vec().to_base32(), Variant::Bech32).unwrap(),
        }
    }
}

pub enum Identity {
    X25519([u8; 32]),
    /// X-Wing decapsulation key (32-byte seed) + the X25519 scalar expanded
    /// from it (for the low-order check that hpke 0.14.1 does not do).
    Pq { seed: [u8; 32], sk: Box<XSk>, sk_x: [u8; 32] },
}

impl Drop for Identity {
    fn drop(&mut self) {
        match self {
            Identity::X25519(k) => k.zeroize(),
            Identity::Pq { seed, sk_x, .. } => {
                seed.zeroize();
                sk_x.zeroize();
            }
        }
    }
}

/// X-Wing key expansion (draft-connolly-cfrg-xwing-kem; x-wing crate
/// `expand_key`): SHAKE256(seed) -> 64-byte ML-KEM seed || 32-byte X25519 sk.
fn xwing_x25519_scalar(seed: &[u8; 32]) -> [u8; 32] {
    use shake::{ExtendableOutput, Update, XofReader};
    let mut h = shake::Shake256::default();
    h.update(seed);
    let mut r = h.finalize_xof();
    let mut skip = [0u8; 64];
    r.read(&mut skip);
    let mut sk_x = [0u8; 32];
    r.read(&mut sk_x);
    sk_x
}

impl Identity {
    pub fn pq_from_seed(seed: [u8; 32]) -> Result<Identity, String> {
        let sk = XSk::from_bytes(&seed).map_err(|e| e.to_string())?;
        let sk_x = xwing_x25519_scalar(&seed);
        // self-check: the derived X25519 public key is the last 32 bytes of pk
        let pk = XWing::sk_to_pk(&sk).to_bytes();
        let px = PublicKey::from(&StaticSecret::from(sk_x));
        if px.as_bytes()[..] != pk[XWING_PK_LEN - 32..] {
            return Err("X-Wing key expansion self-check failed".into());
        }
        Ok(Identity::Pq { seed, sk: Box::new(sk), sk_x })
    }
    pub fn generate_pq() -> Identity {
        let mut seed = [0u8; 32];
        OsRng.fill_bytes(&mut seed);
        Identity::pq_from_seed(seed).unwrap()
    }
    pub fn recipient(&self) -> Recipient {
        match self {
            Identity::X25519(k) => Recipient::X25519(*PublicKey::from(&StaticSecret::from(*k)).as_bytes()),
            Identity::Pq { sk, .. } => Recipient::Pq(Box::new(XWing::sk_to_pk(sk))),
        }
    }
    /// Parses "AGE-SECRET-KEY-1..." or "AGE-SECRET-KEY-PQ-1..." (uppercase
    /// Bech32, as age-keygen writes them).
    pub fn parse(line: &str) -> Result<Identity, String> {
        use bech32::{FromBase32, Variant};
        let (hrp, data, variant) = bech32::decode(line.trim()).map_err(|e| e.to_string())?;
        if variant != Variant::Bech32 {
            return Err("identity must use Bech32".into());
        }
        let raw: [u8; 32] = Vec::<u8>::from_base32(&data).map_err(|e| e.to_string())?.try_into().map_err(|_| "identity length".to_string())?;
        match hrp.as_str() {
            "age-secret-key-" => Ok(Identity::X25519(raw)),
            "age-secret-key-pq-" => Identity::pq_from_seed(raw),
            h => Err(format!("unexpected identity type {h}")),
        }
    }
    pub fn encode(&self) -> String {
        use bech32::{ToBase32, Variant};
        match self {
            Identity::X25519(k) => bech32::encode("age-secret-key-", k.to_base32(), Variant::Bech32).unwrap().to_uppercase(),
            Identity::Pq { seed, .. } => bech32::encode("age-secret-key-pq-", seed.to_base32(), Variant::Bech32).unwrap().to_uppercase(),
        }
    }
}

pub fn parse_identity_file(text: &str) -> Result<Vec<Identity>, String> {
    let ids: Result<Vec<_>, _> = text.lines().map(str::trim).filter(|l| l.starts_with("AGE-SECRET-KEY-")).map(Identity::parse).collect();
    let ids = ids?;
    if ids.is_empty() {
        return Err("no identity in file".into());
    }
    Ok(ids)
}

// ------------------------------------------------------------ hedged RNG

/// A CryptoRng (rand_core 0.10, as used by hpke 0.14.1) that hands out exactly
/// the pre-derived bytes it was built with and panics if asked for more, so a
/// library change in how much randomness it draws cannot go unnoticed.
pub struct HedgeRng {
    buf: Vec<u8>,
    pos: usize,
}

impl HedgeRng {
    pub fn new(bytes: &[u8]) -> Self {
        HedgeRng { buf: bytes.to_vec(), pos: 0 }
    }
    pub fn fully_consumed(&self) -> bool {
        self.pos == self.buf.len()
    }
}

impl Drop for HedgeRng {
    fn drop(&mut self) {
        self.buf.zeroize();
    }
}

impl hpke::rand_core::TryRng for HedgeRng {
    type Error = core::convert::Infallible;
    fn try_next_u32(&mut self) -> Result<u32, Self::Error> {
        let mut b = [0u8; 4];
        self.try_fill_bytes(&mut b)?;
        Ok(u32::from_le_bytes(b))
    }
    fn try_next_u64(&mut self) -> Result<u64, Self::Error> {
        let mut b = [0u8; 8];
        self.try_fill_bytes(&mut b)?;
        Ok(u64::from_le_bytes(b))
    }
    fn try_fill_bytes(&mut self, dst: &mut [u8]) -> Result<(), Self::Error> {
        assert!(self.pos + dst.len() <= self.buf.len(), "HedgeRng exhausted: library drew more randomness than expected");
        dst.copy_from_slice(&self.buf[self.pos..self.pos + dst.len()]);
        self.pos += dst.len();
        Ok(())
    }
}
impl hpke::rand_core::TryCryptoRng for HedgeRng {}

// ------------------------------------------------------------ stanzas

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Stanza {
    pub typ: String,
    pub args: Vec<String>,
    pub body: Vec<u8>,
}

fn encode_stanza(s: &Stanza, out: &mut String) {
    out.push_str("-> ");
    out.push_str(&s.typ);
    for a in &s.args {
        out.push(' ');
        out.push_str(a);
    }
    out.push('\n');
    let b = B64.encode(&s.body);
    let mut i = 0;
    loop {
        let e = std::cmp::min(i + 64, b.len());
        out.push_str(&b[i..e]);
        out.push('\n');
        if e - i < 64 {
            break;
        }
        i = e;
    }
}

fn wrap_x25519(recipient: &[u8; 32], esk_bytes: &mut [u8; 32], file_key: &[u8; 16]) -> Stanza {
    let esk = StaticSecret::from(*esk_bytes);
    esk_bytes.zeroize();
    let epk = PublicKey::from(&esk);
    let shared = esk.diffie_hellman(&PublicKey::from(*recipient));
    assert!(shared.was_contributory(), "non-contributory X25519 (low-order recipient?)");
    let mut salt = [0u8; 64];
    salt[..32].copy_from_slice(epk.as_bytes());
    salt[32..].copy_from_slice(recipient);
    let mut wrap_key = hkdf32(&salt, X25519_LABEL, shared.as_bytes());
    let body = ChaCha20Poly1305::new(&Key::from(wrap_key)).encrypt(&Nonce::default(), &file_key[..]).expect("wrap");
    wrap_key.zeroize();
    Stanza { typ: "X25519".into(), args: vec![B64.encode(epk.as_bytes())], body }
}

fn wrap_pq(pk: &XPk, rand64: &[u8; XWING_ENCAP_RAND], file_key: &[u8; 16]) -> Stanza {
    let mut rng = HedgeRng::new(rand64);
    let (enc, mut ctx) = hpke::setup_sender_with_rng::<HAead, HKdf, XWing>(&OpModeS::Base, pk, PQ_LABEL, &mut rng).expect("X-Wing encap");
    assert!(rng.fully_consumed(), "hpke drew less randomness than expected");
    let body = ctx.seal(file_key, b"").expect("HPKE seal");
    Stanza { typ: PQ_TYPE.into(), args: vec![B64.encode(enc.to_bytes())], body }
}

/// Refuses to mix PQ and classic recipients (age spec SHOULD NOT; Go age 1.3.2
/// refuses with "can't mix post-quantum and classic recipients").
pub fn check_recipient_set(recips: &[Recipient]) -> Result<(), String> {
    if recips.is_empty() {
        return Err("no recipients".into());
    }
    let pq = recips.iter().filter(|r| r.is_pq()).count();
    if pq != 0 && pq != recips.len() {
        return Err("E_MIXED_RECIPIENTS: can't mix post-quantum and classic recipients".into());
    }
    Ok(())
}

pub struct NewHeader {
    /// header bytes || 16-byte payload nonce (object bytes [0, prefix_len)).
    pub prefix: Vec<u8>,
    pub header_len: usize,
    pub payload_key: [u8; 32],
}

/// Generates a fresh age v1 header for `recips` + payload nonce. The file key
/// never leaves this function. `seed_override` is TEST-ONLY (project vectors).
pub fn new_header(recips: &[Recipient], context: &[u8; 32], seed_override: Option<[u8; 32]>) -> Result<NewHeader, String> {
    new_header_opts(recips, context, seed_override, false, false)
}

/// `allow_mixed` and `grease` are TEST-ONLY (negative project vectors / A2-S4):
/// they produce valid age files that the Reliquary profile must reject.
pub fn new_header_opts(recips: &[Recipient], context: &[u8; 32], seed_override: Option<[u8; 32]>, allow_mixed: bool, grease: bool) -> Result<NewHeader, String> {
    if !allow_mixed {
        check_recipient_set(recips)?;
    }
    let mut seed = seed_override.unwrap_or_else(|| {
        let mut s = [0u8; 32];
        OsRng.fill_bytes(&mut s);
        s
    });
    let mut file_key = [0u8; 16];
    hkdf_into(context, b"reliquary/v1/hedge/file-key", &seed, &mut file_key);
    let mut nonce = [0u8; 16];
    hkdf_into(context, b"reliquary/v1/hedge/payload-nonce", &seed, &mut nonce);
    let mut header = String::from(VERSION_LINE);
    header.push('\n');
    for (i, r) in recips.iter().enumerate() {
        let st = match r {
            Recipient::X25519(pk) => {
                // i = 0 keeps CE spike 2's label so a one-stanza X25519 header is unchanged.
                let label = if i == 0 { "reliquary/v1/hedge/x25519-ephemeral".to_string() } else { format!("reliquary/v1/hedge/x25519-ephemeral/{i}") };
                let mut esk = hkdf32(context, label.as_bytes(), &seed);
                wrap_x25519(pk, &mut esk, &file_key)
            }
            Recipient::Pq(pk) => {
                let mut r64 = [0u8; XWING_ENCAP_RAND];
                hkdf_into(context, format!("reliquary/v1/hedge/xwing-encap/{i}").as_bytes(), &seed, &mut r64);
                let st = wrap_pq(pk, &r64, &file_key);
                r64.zeroize();
                st
            }
        };
        encode_stanza(&st, &mut header);
    }
    if grease {
        encode_stanza(&Stanza { typ: "reliquary-grease".into(), args: vec!["x".into()], body: vec![0x42; 7] }, &mut header);
    }
    seed.zeroize();
    header.push_str("---");
    let mut mac_key = hkdf32(&[], b"header", &file_key);
    let mac = hmac_sha256(&mac_key, &[header.as_bytes()]);
    mac_key.zeroize();
    header.push(' ');
    header.push_str(&B64.encode(mac));
    header.push('\n');
    let header_len = header.len();
    let payload_key = hkdf32(&nonce, b"payload", &file_key);
    file_key.zeroize();
    let mut prefix = header.into_bytes();
    prefix.extend_from_slice(&nonce);
    Ok(NewHeader { prefix, header_len, payload_key })
}

// ------------------------------------------------------------ decoding

/// Decoder outcome classes, aligned with the CCTV `expect` values.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OpenErr {
    /// "header failure": malformed header or malformed stanza of a known type.
    Header(String),
    /// "no match": no identity unwrapped any stanza.
    NoMatch,
    /// "HMAC failure"
    Hmac,
    /// "payload failure"
    Payload(String),
}

impl OpenErr {
    pub fn class(&self) -> &'static str {
        match self {
            OpenErr::Header(_) => "header failure",
            OpenErr::NoMatch => "no match",
            OpenErr::Hmac => "HMAC failure",
            OpenErr::Payload(_) => "payload failure",
        }
    }
}

impl std::fmt::Display for OpenErr {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OpenErr::Header(m) => write!(f, "header failure: {m}"),
            OpenErr::NoMatch => write!(f, "no identity matched any of the recipients"),
            OpenErr::Hmac => write!(f, "bad header MAC"),
            OpenErr::Payload(m) => write!(f, "payload failure: {m}"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Header {
    pub stanzas: Vec<Stanza>,
    pub mac: [u8; 32],
    /// Bytes covered by the MAC: everything up to and including "---".
    pub mac_input_len: usize,
    /// Header length including the final "\n" after the MAC.
    pub len: usize,
}

fn hdr(m: impl Into<String>) -> OpenErr {
    OpenErr::Header(m.into())
}

/// Canonical unpadded base64 (rejects padding, non-canonical trailing bits,
/// and any non-alphabet byte including CR).
pub fn b64_canonical(s: &str) -> Result<Vec<u8>, String> {
    let v = B64.decode(s).map_err(|e| format!("base64: {e}"))?;
    if B64.encode(&v) != s {
        return Err("non-canonical base64".into());
    }
    Ok(v)
}

fn is_arg(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| (0x21..=0x7e).contains(&b))
}

/// Strictly parses an age v1 header at the start of `buf`.
pub fn parse_header(buf: &[u8]) -> Result<Header, OpenErr> {
    let mut pos = 0usize;
    let next_line = |pos: &mut usize| -> Result<String, OpenErr> {
        let rest = &buf[*pos..];
        let n = rest.iter().position(|&b| b == b'\n').ok_or_else(|| hdr("unexpected end of header (no newline)"))?;
        if *pos + n + 1 > MAX_HEADER_LEN {
            return Err(hdr("header too long"));
        }
        let line = std::str::from_utf8(&rest[..n]).map_err(|_| hdr("header is not ASCII"))?.to_string();
        if !line.is_ascii() {
            return Err(hdr("header is not ASCII"));
        }
        *pos += n + 1;
        Ok(line)
    };
    let v = next_line(&mut pos)?;
    if v != VERSION_LINE {
        return Err(hdr(if v.starts_with("age-encryption.org/") { "unsupported version" } else { "not an age file" }));
    }
    let mut stanzas = vec![];
    loop {
        let line = next_line(&mut pos)?;
        if let Some(rest) = line.strip_prefix("-> ") {
            if stanzas.len() >= MAX_STANZAS {
                return Err(hdr("too many stanzas"));
            }
            let fields: Vec<&str> = rest.split(' ').collect();
            if fields.iter().any(|f| !is_arg(f)) {
                return Err(hdr("invalid stanza argument"));
            }
            let mut body = vec![];
            loop {
                let bl = next_line(&mut pos)?;
                if bl.len() > 64 {
                    return Err(hdr("stanza body line too long"));
                }
                body.extend(b64_canonical(&bl).map_err(|e| hdr(format!("stanza body: {e}")))?);
                if bl.len() < 64 {
                    break;
                }
            }
            stanzas.push(Stanza { typ: fields[0].to_string(), args: fields[1..].iter().map(|s| s.to_string()).collect(), body });
        } else if let Some(m) = line.strip_prefix("--- ") {
            if stanzas.is_empty() {
                return Err(hdr("no recipient stanzas"));
            }
            let mac: [u8; 32] = b64_canonical(m).map_err(|e| hdr(format!("MAC: {e}")))?.try_into().map_err(|_| hdr("MAC length"))?;
            return Ok(Header { stanzas, mac, mac_input_len: pos - m.len() - 2, len: pos });
        } else {
            return Err(hdr("unexpected line in header"));
        }
    }
}

/// Unwraps the file key from one stanza for one identity.
/// Ok(None) = not for this identity (try the next one); Err = header failure.
fn unwrap_one(st: &Stanza, id: &Identity, strict_low_order: bool) -> Result<Option<[u8; 16]>, OpenErr> {
    match (id, st.typ.as_str()) {
        (Identity::X25519(sk), "X25519") => {
            if st.args.len() != 1 {
                return Err(hdr("invalid X25519 stanza arguments"));
            }
            let share: [u8; 32] = b64_canonical(&st.args[0]).map_err(|e| hdr(format!("X25519 share: {e}")))?.try_into().map_err(|_| hdr("X25519 share length"))?;
            if st.body.len() != 32 {
                return Err(hdr("X25519 stanza body length"));
            }
            let sk = StaticSecret::from(*sk);
            let pk = PublicKey::from(&sk);
            let shared = sk.diffie_hellman(&PublicKey::from(share));
            if !shared.was_contributory() {
                return Err(hdr("X25519 low-order share (all-zero shared secret)"));
            }
            let mut salt = [0u8; 64];
            salt[..32].copy_from_slice(&share);
            salt[32..].copy_from_slice(pk.as_bytes());
            let wk = hkdf32(&salt, X25519_LABEL, shared.as_bytes());
            Ok(ChaCha20Poly1305::new(&Key::from(wk)).decrypt(&Nonce::default(), st.body.as_slice()).ok().map(|v| v.try_into().unwrap()))
        }
        (Identity::Pq { sk, sk_x, .. }, PQ_TYPE) => {
            if st.args.len() != 1 {
                return Err(hdr("invalid mlkem768x25519 stanza arguments"));
            }
            let enc = b64_canonical(&st.args[0]).map_err(|e| hdr(format!("mlkem768x25519 enc: {e}")))?;
            if enc.len() != XWING_ENC_LEN {
                return Err(hdr("mlkem768x25519 enc length"));
            }
            if st.body.len() != 32 {
                return Err(hdr("mlkem768x25519 stanza body length"));
            }
            if strict_low_order {
                let ct_x: [u8; 32] = enc[XWING_ENC_LEN - 32..].try_into().unwrap();
                let ss = StaticSecret::from(*sk_x).diffie_hellman(&PublicKey::from(ct_x));
                if !ss.was_contributory() {
                    return Err(hdr("mlkem768x25519 X25519 share is low-order (all-zero shared secret)"));
                }
            }
            let enc = XEnc::from_bytes(&enc).map_err(|e| hdr(format!("mlkem768x25519 enc: {e}")))?;
            let mut ctx = match hpke::setup_receiver::<HAead, HKdf, XWing>(&OpModeR::Base, sk, &enc, PQ_LABEL) {
                Ok(c) => c,
                Err(e) => return Err(hdr(format!("X-Wing decap: {e}"))),
            };
            Ok(ctx.open(&st.body, b"").ok().map(|v| v.try_into().unwrap()))
        }
        _ => Ok(None),
    }
}

/// Finds the file key (identity-major, like Go age) and verifies the header
/// MAC. Returns (file_key, header).
pub fn open_header(buf: &[u8], ids: &[Identity], strict_low_order: bool) -> Result<([u8; 16], Header), OpenErr> {
    let h = parse_header(buf)?;
    if h.stanzas.iter().any(|s| s.typ == "scrypt") && h.stanzas.len() != 1 {
        return Err(hdr("an scrypt stanza must be the only stanza"));
    }
    let mut fk = None;
    'outer: for id in ids {
        for st in &h.stanzas {
            if let Some(k) = unwrap_one(st, id, strict_low_order)? {
                fk = Some(k);
                break 'outer;
            }
        }
    }
    let mut fk = fk.ok_or(OpenErr::NoMatch)?;
    let mut mac_key = hkdf32(&[], b"header", &fk);
    let mut m = <Hmac<Sha256> as KeyInit>::new_from_slice(&mac_key).unwrap();
    mac_key.zeroize();
    m.update(&buf[..h.mac_input_len]);
    if m.verify_slice(&h.mac).is_err() {
        fk.zeroize();
        return Err(OpenErr::Hmac);
    }
    Ok((fk, h))
}

/// Opens the prefix of an object: returns (payload_key, prefix_len, header).
/// Needs the header plus the 16-byte nonce in `buf`.
pub fn open_prefix(buf: &[u8], ids: &[Identity], strict_low_order: bool) -> Result<([u8; 32], usize, Header), OpenErr> {
    let (mut fk, h) = open_header(buf, ids, strict_low_order)?;
    if buf.len() < h.len + 16 {
        fk.zeroize();
        return Err(OpenErr::Header("missing or short payload nonce".into()));
    }
    let pk = hkdf32(&buf[h.len..h.len + 16], b"payload", &fk);
    fk.zeroize();
    Ok((pk, h.len + 16, h))
}

/// The base64 header MAC of a header (binds a metadata record to one
/// encrypted instance).
pub fn header_mac_b64(prefix: &[u8]) -> Result<String, String> {
    let h = parse_header(prefix).map_err(|e| e.to_string())?;
    Ok(B64.encode(h.mac))
}

// ------------------------------------------------------------ payload

use crate::format::{chunk_nonce, CHUNK_CT, TAG};

/// Streaming STREAM decryption over a reader positioned just after the
/// payload nonce. Only authenticated plaintext is passed to `sink`. Mirrors
/// the age spec rules: a missing final chunk, an empty non-first final chunk,
/// trailing data after the final chunk and any tag failure are payload failures.
pub fn decrypt_payload(payload_key: &[u8; 32], mut r: impl std::io::Read, mut sink: impl FnMut(&[u8]) -> std::io::Result<()>) -> Result<u64, OpenErr> {
    let aead = ChaCha20Poly1305::new(&Key::from(*payload_key));
    let pf = |m: &str| OpenErr::Payload(m.to_string());
    let mut buf = vec![0u8; CHUNK_CT as usize + 1];
    let mut have = 0usize;
    let fill = |r: &mut dyn std::io::Read, buf: &mut [u8], have: &mut usize| -> Result<(), OpenErr> {
        while *have < buf.len() {
            let k = r.read(&mut buf[*have..]).map_err(|e| OpenErr::Payload(format!("read: {e}")))?;
            if k == 0 {
                break;
            }
            *have += k;
        }
        Ok(())
    };
    let mut c = 0u64;
    let mut total = 0u64;
    loop {
        fill(&mut r, &mut buf, &mut have)?;
        if have == 0 {
            return Err(pf(if c == 0 { "no chunks" } else { "missing final chunk (truncated)" }));
        }
        let n = std::cmp::min(have, CHUNK_CT as usize);
        if n < TAG as usize {
            return Err(pf("chunk shorter than a tag"));
        }
        let more = have > CHUNK_CT as usize;
        let dec = |last: bool| aead.decrypt(&Nonce::from(chunk_nonce(c, last)), &buf[..n]).ok();
        if more {
            match dec(false) {
                Some(pt) => {
                    sink(&pt).map_err(|e| pf(&e.to_string()))?;
                    total += pt.len() as u64;
                }
                None => {
                    // A chunk that authenticates as *final* but is followed by
                    // more data: release it (it is authenticated), then fail.
                    if let Some(pt) = dec(true) {
                        sink(&pt).map_err(|e| pf(&e.to_string()))?;
                        return Err(pf("trailing data after the final chunk"));
                    }
                    return Err(pf("chunk authentication failed"));
                }
            }
            buf.copy_within(n..have, 0);
            have -= n;
            c += 1;
        } else {
            match dec(true) {
                Some(pt) => {
                    if pt.is_empty() && c > 0 {
                        return Err(pf("final chunk is empty"));
                    }
                    sink(&pt).map_err(|e| pf(&e.to_string()))?;
                    total += pt.len() as u64;
                    return Ok(total);
                }
                None => {
                    // A full chunk at EOF that authenticates as *non-final*:
                    // release it (authenticated), then report the truncation.
                    if n == CHUNK_CT as usize {
                        if let Some(pt) = dec(false) {
                            sink(&pt).map_err(|e| pf(&e.to_string()))?;
                            return Err(pf("missing final chunk (truncated at a chunk boundary)"));
                        }
                    }
                    return Err(pf("chunk authentication failed"));
                }
            }
        }
    }
}

/// Full-file decrypt (header + payload) for a whole age file in memory or a
/// reader. Returns the number of plaintext bytes.
pub fn decrypt_file(mut r: impl std::io::Read, ids: &[Identity], strict_low_order: bool, sink: impl FnMut(&[u8]) -> std::io::Result<()>) -> Result<u64, OpenErr> {
    // Read up to MAX_HEADER_LEN + 16 bytes for the header and nonce.
    let mut head = vec![0u8; MAX_HEADER_LEN + 16];
    let mut have = 0;
    while have < head.len() {
        let k = r.read(&mut head[have..]).map_err(|e| hdr(format!("read: {e}")))?;
        if k == 0 {
            break;
        }
        have += k;
    }
    head.truncate(have);
    let (mut pk, prefix_len, _) = open_prefix(&head, ids, strict_low_order)?;
    use std::io::Read;
    let rest = std::io::Cursor::new(head[prefix_len..].to_vec()).chain(r);
    let res = decrypt_payload(&pk, rest, sink);
    pk.zeroize();
    res
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pq_roundtrip_and_mixing_refused() {
        let id = Identity::generate_pq();
        let r = id.recipient();
        let ctx = [3u8; 32];
        let nh = new_header(&[r], &ctx, None).unwrap();
        assert_eq!(nh.header_len, 1627, "one-stanza PQ header length");
        let (pk, pl, h) = open_prefix(&nh.prefix, &[id], true).unwrap();
        assert_eq!(pk, nh.payload_key);
        assert_eq!(pl, 1643);
        assert_eq!(h.stanzas.len(), 1);
        let x = Identity::X25519([5u8; 32]);
        let mixed = [Identity::generate_pq().recipient(), x.recipient()];
        assert!(new_header(&mixed, &ctx, None).is_err());
    }

    #[test]
    fn two_pq_and_x25519_lengths() {
        let a = Identity::generate_pq();
        let b = Identity::generate_pq();
        let nh = new_header(&[a.recipient(), b.recipient()], &[1u8; 32], None).unwrap();
        assert_eq!(nh.header_len, 3184);
        assert!(open_prefix(&nh.prefix, &[b], true).is_ok());
        let x = Identity::X25519([9u8; 32]);
        let nx = new_header(&[x.recipient()], &[1u8; 32], None).unwrap();
        assert_eq!(nx.header_len, 168);
    }

    #[test]
    fn seeded_header_is_deterministic() {
        let a = Identity::generate_pq();
        let s = Some([7u8; 32]);
        let h1 = new_header(&[a.recipient()], &[2u8; 32], s).unwrap();
        let h2 = new_header(&[a.recipient()], &[2u8; 32], s).unwrap();
        assert_eq!(h1.prefix, h2.prefix);
        let h3 = new_header(&[a.recipient()], &[4u8; 32], s).unwrap();
        assert_ne!(h1.prefix, h3.prefix, "different context => different header even with a repeated seed");
    }

    #[test]
    fn recipient_identity_encodings_roundtrip() {
        let a = Identity::generate_pq();
        let s = a.recipient().encode();
        assert!(s.starts_with("age1pq1"));
        let back = Recipient::parse(&s).unwrap();
        assert_eq!(back.encode(), s);
        assert!(Recipient::parse(&s.to_uppercase()).is_err());
        let i2 = Identity::parse(&a.encode()).unwrap();
        assert_eq!(i2.recipient().encode(), s);
    }
}
