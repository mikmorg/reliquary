#!/usr/bin/env python3
"""E2-S2 metric feasibility: field inventory and trust-model rule check (THROWAWAY spike code).

For every metric M1-M10 in docs/research/e2-v1-scope-metrics-pilot.md section 3, list the data fields it
needs, where each field is produced, the route it takes to the place the metric is computed, and
whether it is derived from file content or names. Then apply the trust-model rules taken from
ADR-0001 section 2, ADR-0002 section 2, CLAUDE.md and PLAN (no third-party analytics, no email click
tracking) and report, per metric, whether every field has a compliant source.

A few deliberately bad "variant" designs are included so the check is shown to catch violations
(they are not proposals).
"""
import json
import sys

# Routes a field can take to where the metric is computed.
ROUTES = {
    "device_local": "stays on the device (used only on the device)",
    "enc_homelab": "encrypted on the device to the homelab public key, relayed through R2 as ciphertext",
    "homelab_local": "produced and kept at the homelab (catalog, receipt ledger, admin tool logs)",
    "cloud_plain": "held or seen in plaintext by the Worker / D1 / R2 metadata",
    "email_body": "text of an email sent by the Worker through an email provider (plaintext to both)",
    "owner_log": "the owner's own written log, kept at the homelab",
    "session_paper": "paper sheet in a usability session (H3 FAM -> AGG)",
    "third_party": "any third-party analytics or tracking service",
}

# What the cloud may hold in plaintext, with the settled text that allows it.
CLOUD_PLAIN_ALLOWED = {
    "account_identity": "ADR-0002 s2: name and email stored in plain text in the control plane",
    "device_activity_ts": "ADR-0002 s2: per-device activity timestamps stored in plain text",
    "invite_state": "ADR-0002 s2: hash of the invite code, its expiry and state unused->redeemed",
    "opaque_dedup_state": "ADR-0001 s2/s4: opaque dedup IDs, claim/commit state",
    "ciphertext_object": "ADR-0001 s1/s2: R2 holds ciphertext; object size and count are inherent to storing it (not stated in the ADR; size padding is D1/F3's topic)",
    "email_send_event": "ADR-0002 s2: the Worker sends nudge email, so it knows that and when it sent one",
    "nudge_text_from_activity": "ADR-0002 s2 example: 'your laptop hasn't backed up in 14 days' (derived from activity timestamps only)",
}

# field id -> properties
#   producer: device | worker | homelab | owner | session
#   route: key of ROUTES
#   content_derived: True if derived from file content, names, paths, sizes of plaintext files or EXIF
#   per_file: True if the field identifies individual files (not an aggregate or opaque ID set digest)
#   cloud_category: for cloud_plain / email_body fields, the CLOUD_PLAIN_ALLOWED key it relies on
#   consent_since: report version that introduced the field (Syncthing 'since' pattern); None = operational
FIELDS = {
    # --- Worker (plaintext, allowed by ADR-0002) ---
    "redeemed_at": dict(producer="worker", route="cloud_plain", content_derived=False, per_file=False,
                        cloud_category="invite_state", consent_since=None,
                        desc="Invite redemption time (Worker clock)"),
    "device_last_seen_at": dict(producer="worker", route="cloud_plain", content_derived=False, per_file=False,
                                cloud_category="device_activity_ts", consent_since=None,
                                desc="Last authenticated request per device (Worker clock)"),
    "email_nudge_sent_at": dict(producer="worker", route="cloud_plain", content_derived=False, per_file=False,
                                cloud_category="email_send_event", consent_since=None,
                                desc="An email nudge was sent to a person, with its kind (stale-device etc.)"),
    "report_blob_arrival": dict(producer="worker", route="cloud_plain", content_derived=False, per_file=False,
                                cloud_category="ciphertext_object", consent_since=None,
                                desc="Arrival time and (padded) size of an encrypted device report object"),
    # --- Homelab (local) ---
    "receipt_ledger": dict(producer="homelab", route="homelab_local", content_derived=True, per_file=True,
                           cloud_category=None, consent_since=None,
                           desc="Every receipt entry signed per device (A3): record_id, dedup_id, size, committed_at"),
    "catalog": dict(producer="homelab", route="homelab_local", content_derived=True, per_file=True,
                    cloud_category=None, consent_since=None,
                    desc="Plaintext catalog (ADR-0001 s2)"),
    "restore_drill_log": dict(producer="homelab", route="homelab_local", content_derived=False, per_file=False,
                              cloud_category=None, consent_since=None,
                              desc="Admin tool log of each sampled drill: device, item count, owner minutes"),
    # --- Device, sent encrypted to the homelab ---
    "first_receipt_verified_mono": dict(producer="device", route="enc_homelab", content_derived=False, per_file=False,
                                        cloud_category=None, consent_since=None,
                                        desc="Time from enrollment to first verified receipt (device monotonic clock, A3 s9)"),
    "discovered_accepted_items_bytes": dict(producer="device", route="enc_homelab", content_derived=True, per_file=False,
                                            cloud_category=None, consent_since=None,
                                            desc="Counts and bytes of keepsakes discovered and accepted (not excluded)"),
    "cloud_only_items_bytes": dict(producer="device", route="enc_homelab", content_derived=True, per_file=False,
                                   cloud_category=None, consent_since=None,
                                   desc="Counts and bytes in the cloud-only side state (A3)"),
    "receipted_items_bytes": dict(producer="device", route="enc_homelab", content_derived=True, per_file=False,
                                  cloud_category=None, consent_since=None,
                                  desc="Counts and bytes the device holds verified receipts for"),
    "shown_stored_digest": dict(producer="device", route="enc_homelab", content_derived=False, per_file=False,
                                cloud_category=None, consent_since=None,
                                desc="Count + SHA-256 over sorted record_ids the UI shows as 'stored at home'"),
    "gone_before_safe_count": dict(producer="device", route="enc_homelab", content_derived=False, per_file=False,
                                   cloud_category=None, consent_since=None,
                                   desc="Items that entered the gone-before-safe side state (A3)"),
    "nudge_shown_snoozed_muted": dict(producer="device", route="enc_homelab", content_derived=False, per_file=False,
                                      cloud_category=None, consent_since=2,
                                      desc="In-app / OS nudges shown, snoozed, muted, by kind"),
    "restore_check_result": dict(producer="device", route="enc_homelab", content_derived=False, per_file=False,
                                 cloud_category=None, consent_since=None,
                                 desc="Restored items whose SHA-256 matched the restore manifest, and mismatches"),
    # --- Owner and sessions ---
    "support_minutes_by_cause": dict(producer="owner", route="owner_log", content_derived=False, per_file=False,
                                     cloud_category=None, consent_since=None,
                                     desc="One line per incident: date, device, minutes, cause"),
    "audit_surprise_gaps": dict(producer="owner", route="owner_log", content_derived=False, per_file=False,
                                cloud_category=None, consent_since=None,
                                desc="Count of keepsake locations found in an audit that discovery missed (counts only)"),
    "enrollment_observation": dict(producer="session", route="session_paper", content_derived=False, per_file=False,
                                   cloud_category=None, consent_since=None,
                                   desc="Observer's sheet: unaided yes/no, minutes, assists"),
    "sus_seq_sheet": dict(producer="session", route="session_paper", content_derived=False, per_file=False,
                          cloud_category=None, consent_since=None,
                          desc="SUS (10 items) and SEQ (1 item per task) on paper"),
}

# Deliberately non-compliant variants (to show the check catches them). Not proposals.
BAD_FIELDS = {
    "X_cloud_discovered_counts": dict(producer="device", route="cloud_plain", content_derived=True, per_file=False,
                                      cloud_category=None, consent_since=None,
                                      desc="Variant: device posts discovered/receipted counts to the Worker in plaintext"),
    "X_email_link_click": dict(producer="worker", route="cloud_plain", content_derived=False, per_file=False,
                               cloud_category=None, consent_since=None,
                               desc="Variant: tracked redirect link in nudge email (PLAN s3: no click tracking)"),
    "X_email_body_with_counts": dict(producer="worker", route="email_body", content_derived=True, per_file=False,
                                     cloud_category=None, consent_since=None,
                                     desc="Variant: nudge email says '1,203 photos not protected' (needs content-derived counts in the cloud)"),
    "X_hosted_analytics": dict(producer="device", route="third_party", content_derived=False, per_file=False,
                               cloud_category=None, consent_since=2,
                               desc="Variant: a hosted analytics SDK for engagement events"),
    "X_shown_stored_id_list_plain": dict(producer="device", route="cloud_plain", content_derived=False, per_file=True,
                                         cloud_category="opaque_dedup_state", consent_since=None,
                                         desc="Variant: device posts the list of record_ids it shows as stored, in plaintext"),
}

METRICS = {
    "M1": ("Time to first protected keepsake", ["redeemed_at", "first_receipt_verified_mono", "receipt_ledger"]),
    "M2": ("Coverage (bytes and items) at 7 and 30 days", ["discovered_accepted_items_bytes", "cloud_only_items_bytes",
                                                           "receipted_items_bytes", "receipt_ledger"]),
    "M3": ("Surprise gaps found in an audit", ["audit_surprise_gaps"]),
    "M4": ("Owner support minutes", ["support_minutes_by_cause"]),
    "M5": ("Unaided enrollment", ["enrollment_observation", "redeemed_at", "receipt_ledger", "support_minutes_by_cause"]),
    "M6": ("Nudge action vs mute rate", ["email_nudge_sent_at", "nudge_shown_snoozed_muted", "receipt_ledger",
                                         "device_last_seen_at"]),
    "M7": ("Restore-drill success and time", ["restore_drill_log", "restore_check_result"]),
    "M8": ("SUS and SEQ", ["sus_seq_sheet"]),
    "M9": ("False-safe count", ["shown_stored_digest", "receipt_ledger"]),
    "M10": ("Gone-before-safe count", ["gone_before_safe_count"]),
}

BAD_METRICS = {
    "M2-bad": ("Coverage computed in the Worker", ["X_cloud_discovered_counts"]),
    "M6-bad-click": ("Nudge action by email click", ["X_email_link_click"]),
    "M6-bad-body": ("Nudge email quoting counts", ["X_email_body_with_counts"]),
    "M6-bad-sdk": ("Engagement via hosted analytics", ["X_hosted_analytics"]),
    "M9-bad": ("False-safe check with plaintext ID list", ["X_shown_stored_id_list_plain"]),
}


def check_field(fid, f):
    """Return a list of rule violations for one field."""
    v = []
    route = f["route"]
    if route == "third_party":
        v.append("R1 no third-party analytics (PLAN E2; CLAUDE.md trust model)")
    if route in ("cloud_plain", "email_body"):
        cat = f.get("cloud_category")
        if f["content_derived"]:
            v.append("R2 content-derived data in cloud plaintext (ADR-0001 s2: metadata is ciphertext only)")
        if cat not in CLOUD_PLAIN_ALLOWED:
            v.append("R3 cloud plaintext not covered by ADR-0001/0002 accepted categories")
        if f["per_file"]:
            v.append("R4 per-file identifiers in cloud plaintext beyond what the ingest protocol needs")
    if route == "enc_homelab" and f["per_file"]:
        v.append("R5 telemetry must be aggregates or digests, not per-file lists (minimisation; D6/B8)")
    if fid.startswith("X_email_link_click"):
        v.append("R6 no email click tracking (PLAN s3)")
    return v


def run(out=sys.stdout):
    allf = {**FIELDS, **BAD_FIELDS}
    rows = []
    for mid, (name, fields) in {**METRICS, **BAD_METRICS}.items():
        viol = {fid: check_field(fid, allf[fid]) for fid in fields}
        ok = all(not x for x in viol.values())
        rows.append(dict(metric=mid, name=name, compliant=ok,
                         fields=[dict(field=fid, route=allf[fid]["route"],
                                      cloud_basis=CLOUD_PLAIN_ALLOWED.get(allf[fid].get("cloud_category"))
                                      if allf[fid]["route"] in ("cloud_plain", "email_body") else None,
                                      consent_since=allf[fid]["consent_since"],
                                      violations=viol[fid]) for fid in fields]))
    json.dump(rows, out, indent=2)
    return rows


if __name__ == "__main__":
    rows = run(open(sys.argv[1], "w") if len(sys.argv) > 1 else sys.stdout)
    print(file=sys.stderr)
    for r in rows:
        print(f"{r['metric']:<14} {'COMPLIANT' if r['compliant'] else 'VIOLATES':<10} {r['name']}", file=sys.stderr)
        for f in r["fields"]:
            for v in f["violations"]:
                print(f"{'':<16}{f['field']}: {v}", file=sys.stderr)
