//! THROWAWAY SPIKE CODE. Not production.
//!
//! Signed metadata records (device -> homelab, inside age encryption) and
//! signed commit receipts (homelab -> device, relayed by the cloud).
//!
//! Signed-message framing (both kinds): the plaintext is
//!   line1 = compact JSON body
//!   line2 = {"alg":"ed25519","key_id":...,"sig":base64(Ed25519(domain || "\n" || line1))}
//! followed by "\n". Metadata plaintext is then padded with ASCII spaces to a
//! multiple of 512 bytes before encryption.

use base64::{engine::general_purpose::STANDARD as B64P, Engine};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde_json::Value;

pub const META_DOMAIN: &str = "reliquary-meta-v1";
pub const RECEIPT_DOMAIN: &str = "reliquary-commit-v1";
pub const META_PAD: usize = 512;

fn signed_input(domain: &str, line1: &[u8]) -> Vec<u8> {
    [domain.as_bytes(), b"\n", line1].concat()
}

pub fn sign_lines(domain: &str, key_id: &str, body: &Value, sk: &SigningKey) -> Vec<u8> {
    let line1 = serde_json::to_vec(body).unwrap();
    let sig = sk.sign(&signed_input(domain, &line1));
    let line2 = serde_json::to_vec(&serde_json::json!({"alg": "ed25519", "key_id": key_id, "sig": B64P.encode(sig.to_bytes())})).unwrap();
    [line1.as_slice(), b"\n", &line2, b"\n"].concat()
}

/// Parses and verifies a signed two-line message. `lookup` maps key_id to a key.
pub fn verify_lines(
    domain: &str,
    msg: &[u8],
    lookup: &dyn Fn(&str) -> Option<VerifyingKey>,
) -> Result<(Value, String), String> {
    let mut it = msg.splitn(3, |&b| b == b'\n');
    let line1 = it.next().ok_or("missing body line")?;
    let line2 = it.next().ok_or("missing signature line")?;
    let rest = it.next().unwrap_or(b"");
    if !rest.iter().all(|&b| b == b' ') {
        return Err("unexpected trailing data".into());
    }
    let sigv: Value = serde_json::from_slice(line2).map_err(|e| format!("signature line: {e}"))?;
    if sigv["alg"] != "ed25519" {
        return Err("unsupported signature algorithm".into());
    }
    let key_id = sigv["key_id"].as_str().ok_or("key_id")?.to_string();
    let key = lookup(&key_id).ok_or_else(|| format!("unknown signing key {key_id}"))?;
    let sig_bytes: [u8; 64] = B64P
        .decode(sigv["sig"].as_str().ok_or("sig")?)
        .map_err(|_| "sig b64")?
        .try_into()
        .map_err(|_| "sig len")?;
    key.verify(&signed_input(domain, line1), &Signature::from_bytes(&sig_bytes))
        .map_err(|_| "signature verification failed".to_string())?;
    let body: Value = serde_json::from_slice(line1).map_err(|e| format!("body: {e}"))?;
    Ok((body, key_id))
}

pub fn pad_meta(mut v: Vec<u8>) -> Vec<u8> {
    let n = v.len().div_ceil(META_PAD) * META_PAD;
    v.resize(n, b' ');
    v
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
