//! THROWAWAY SPIKE CODE. Not production.
//!
//! Signed metadata records (device -> homelab, inside age encryption) and
//! signed commit receipts (homelab -> device), both framed as C2SP
//! signed-notes (the analyst's provisional F6 envelope):
//!
//!   <text: one line of compact JSON>\n
//!   \n
//!   — <key name> <base64(key_hash[4] || ed25519_sig[64])>\n
//!
//! key_hash = SHA-256(name || "\n" || 0x01 || pubkey)[:4]; the signature
//! covers the text (including its final newline). Padding lives *inside* the
//! JSON (`pad` field) because a signed-note allows no trailing bytes.

use base64::{engine::general_purpose::STANDARD as B64P, Engine};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use serde_json::Value;
use sha2::{Digest, Sha256};

pub const META_KIND: &str = "reliquary.file-meta";
pub const RECEIPT_KIND: &str = "reliquary.commit-receipt";
pub const META_PAD: usize = 512;
const DASH: &str = "\u{2014} ";

pub fn key_hash(name: &str, pk: &VerifyingKey) -> [u8; 4] {
    let mut h = Sha256::new();
    h.update(name.as_bytes());
    h.update(b"\n\x01");
    h.update(pk.as_bytes());
    h.finalize()[..4].try_into().unwrap()
}

fn valid_name(n: &str) -> bool {
    !n.is_empty() && !n.contains(' ') && !n.contains('+') && n.chars().all(|c| !c.is_control())
}

/// Signs `text` (must end with '\n', no control chars other than '\n').
pub fn sign_note(text: &str, name: &str, sk: &SigningKey) -> Vec<u8> {
    assert!(text.ends_with('\n') && valid_name(name));
    assert!(text.chars().all(|c| c == '\n' || !c.is_control()));
    let sig = sk.sign(text.as_bytes());
    let mut kh_sig = key_hash(name, &sk.verifying_key()).to_vec();
    kh_sig.extend_from_slice(&sig.to_bytes());
    format!("{text}\n{DASH}{name} {}\n", B64P.encode(kh_sig)).into_bytes()
}

/// TEST-ONLY adversary helper: like sign_note but with a chosen key hash
/// (e.g. the victim device's, computed from its public key).
pub fn sign_note_forged_kh(text: &str, name: &str, sk: &SigningKey, kh: [u8; 4]) -> Vec<u8> {
    let sig = sk.sign(text.as_bytes());
    let mut kh_sig = kh.to_vec();
    kh_sig.extend_from_slice(&sig.to_bytes());
    format!("{text}\n{DASH}{name} {}\n", B64P.encode(kh_sig)).into_bytes()
}

/// Verifies a signed note with exactly one signature from a known key.
/// Returns (text, key name).
pub fn open_note(msg: &[u8], lookup: &dyn Fn(&str) -> Option<VerifyingKey>) -> Result<(String, String), String> {
    let s = std::str::from_utf8(msg).map_err(|_| "E_RECORD_FORMAT: note is not UTF-8")?;
    let split = s.rfind("\n\n").ok_or("E_RECORD_FORMAT: no signature block")?;
    let text = &s[..split + 1];
    let sigs = &s[split + 2..];
    if text.chars().any(|c| c != '\n' && c.is_control()) {
        return Err("E_RECORD_FORMAT: control character in note text".into());
    }
    let lines: Vec<&str> = sigs.split_terminator('\n').collect();
    if !sigs.ends_with('\n') || lines.len() != 1 {
        return Err("E_RECORD_FORMAT: expected exactly one signature line".into());
    }
    let l = lines[0].strip_prefix(DASH).ok_or("E_RECORD_FORMAT: bad signature line")?;
    let (name, b64) = l.split_once(' ').ok_or("E_RECORD_FORMAT: bad signature line")?;
    if !valid_name(name) {
        return Err("E_RECORD_FORMAT: bad key name".into());
    }
    let raw = B64P.decode(b64).map_err(|_| "E_RECORD_FORMAT: signature base64")?;
    if raw.len() != 68 {
        return Err("E_RECORD_FORMAT: signature length".into());
    }
    let key = lookup(name).ok_or_else(|| format!("E_SIG_UNKNOWN_KEY: unknown signing key {name}"))?;
    if raw[..4] != key_hash(name, &key) {
        return Err("E_SIG_KEY_HASH: key hash does not match the registered key".into());
    }
    let sig = Signature::from_bytes(&raw[4..].try_into().unwrap());
    key.verify_strict(text.as_bytes(), &sig).map_err(|_| "E_SIG_INVALID: signature verification failed".to_string())?;
    Ok((text.to_string(), name.to_string()))
}

/// Builds the one-line JSON text, padding the whole signed note to a multiple
/// of META_PAD bytes with a `pad` field (sizes leak less across records).
pub fn padded_text(mut body: Value, name: &str) -> String {
    body["pad"] = Value::String(String::new());
    let base = serde_json::to_string(&body).unwrap().len() + 1; // + "\n"
    // note = text + "\n" + "— " + name + " " + 92 base64 chars + "\n"
    let sig_len = 1 + DASH.len() + name.len() + 1 + 92 + 1;
    let total = base + sig_len;
    let pad = total.div_ceil(META_PAD) * META_PAD - total;
    body["pad"] = Value::String(" ".repeat(pad));
    let t = serde_json::to_string(&body).unwrap() + "\n";
    debug_assert_eq!((t.len() + sig_len) % META_PAD, 0);
    t
}

pub fn parse_text_json(text: &str) -> Result<Value, String> {
    let line = text.strip_suffix('\n').ok_or("E_RECORD_FORMAT: text must end with a newline")?;
    if line.contains('\n') {
        return Err("E_RECORD_FORMAT: record text must be one line".into());
    }
    serde_json::from_str(line).map_err(|e| format!("E_RECORD_FORMAT: {e}"))
}

pub fn load_signing_key(path: &std::path::Path) -> Result<SigningKey, String> {
    let raw = std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let seed: [u8; 32] = raw.try_into().map_err(|_| "signing key file must be 32 bytes")?;
    Ok(SigningKey::from_bytes(&seed))
}

pub fn pk_b64(sk: &SigningKey) -> String {
    B64P.encode(sk.verifying_key().to_bytes())
}

pub fn parse_pk_b64(s: &str) -> Result<VerifyingKey, String> {
    let b: [u8; 32] = B64P.decode(s).map_err(|e| e.to_string())?.try_into().map_err(|_| "pk len".to_string())?;
    VerifyingKey::from_bytes(&b).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn note_roundtrip_and_tamper() {
        let sk = SigningKey::from_bytes(&[1u8; 32]);
        let t = padded_text(serde_json::json!({"a": 1}), "dev-1");
        let n = sign_note(&t, "dev-1", &sk);
        assert_eq!(n.len() % META_PAD, 0);
        let lk = |k: &str| if k == "dev-1" { Some(sk.verifying_key()) } else { None };
        assert!(open_note(&n, &lk).is_ok());
        let mut bad = n.clone();
        bad[2] ^= 1;
        assert!(open_note(&bad, &lk).unwrap_err().starts_with("E_"));
    }
}
