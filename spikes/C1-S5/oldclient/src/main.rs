//! C1-S5 old-client probe (throwaway). Two decoding profiles of the SAME v1 schema:
//! - `naive`: closed enum for the per-item status, as a first implementation would write it;
//! - `tolerant`: an `Unknown` catch-all variant (`#[serde(other)]`), the rule the API spec would impose.
//! Unknown object fields are ignored in both (serde's default; no `deny_unknown_fields`).
use serde::Deserialize;
use std::env;

#[derive(Debug, Deserialize)]
#[allow(non_camel_case_types, clippy::upper_case_acronyms, dead_code)]
enum StatusNaive { MISSING, IN_FLIGHT, COMMITTED }

#[derive(Debug, Deserialize)]
#[allow(non_camel_case_types, clippy::upper_case_acronyms, dead_code)]
enum StatusTolerant { MISSING, IN_FLIGHT, COMMITTED, #[serde(other)] Unknown }

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct Item<S> { id: String, status: S }

#[derive(Debug, Deserialize)]
struct CheckResp<S> { results: Vec<Item<S>> }

#[derive(Debug, Deserialize)]
struct Problem { code: String, min_version: Option<String> }

fn run<S: for<'de> Deserialize<'de> + std::fmt::Debug>(base: &str, mode: &str, version: &str, ids: &[String]) -> String {
    let resp = ureq::post(&format!("{base}/v1/check"))
        .set("Reliquary-Client", &format!("desktop/{version}"))
        .set("X-Test-Server-Mode", mode)
        .send_json(serde_json::json!({ "ids": ids }));
    let (status, ctype, body) = match resp {
        Ok(r) => (r.status(), r.content_type().to_string(), r.into_string().unwrap_or_default()),
        Err(ureq::Error::Status(code, r)) => (code, r.content_type().to_string(), r.into_string().unwrap_or_default()),
        Err(e) => return format!("transport_error: {e}"),
    };
    if ctype == "application/problem+json" {
        return match serde_json::from_str::<Problem>(&body) {
            Ok(p) if p.code == "update_required" => format!("UPDATE_REQUIRED (http {status}, min_version {})", p.min_version.unwrap_or_default()),
            Ok(p) => format!("problem {} (http {status})", p.code),
            Err(e) => format!("problem body undecodable: {e}"),
        };
    }
    match serde_json::from_str::<CheckResp<S>>(&body) {
        Ok(r) => {
            let unknown = r.results.iter().filter(|i| format!("{:?}", i.status) == "Unknown").count();
            format!("OK (http {status}, {} items, {} Unknown)", r.results.len(), unknown)
        }
        Err(e) => format!("DECODE_ERROR (http {status}): {e}"),
    }
}

fn main() {
    let base = env::args().nth(1).unwrap_or_else(|| "http://127.0.0.1:8790".into());
    let version = env::args().nth(2).unwrap_or_else(|| env!("CARGO_PKG_VERSION").into());
    let ids: Vec<String> = (0..8).map(|i| format!("{:064x}", i + 1)).collect();
    for mode in ["v1", "v2-add-field", "v2-add-enum", "v2-rename", "v2-break-gated"] {
        println!("{{\"mode\":\"{mode}\",\"client\":\"{version}\",\"naive\":{:?},\"tolerant\":{:?}}}",
            run::<StatusNaive>(&base, mode, &version, &ids), run::<StatusTolerant>(&base, mode, &version, &ids));
    }
}
