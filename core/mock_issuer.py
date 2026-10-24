"""Mock issuing-authority adapter. Replace with real API adapters ONLY when access is authorized.
Statuses mirror the PRD. 'source_unavailable' / 'pending' are NOT failed authenticity checks.
Test hooks (reference prefixes): UNAVAIL* always unreachable, FLAKY* unreachable on attempt 1 only,
PENDING* never concludes (stays pending)."""
import json, os
from datetime import datetime

REG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_registry.json")
CONCLUSIVE = ("verified", "mismatch_detected", "expired")


def _parse(d):
    return datetime.strptime(d.replace("/", "-"), "%d-%m-%Y").date()


def verify(fields, eval_date, registry=None, attempt=1):
    if registry is None:
        with open(REG_PATH) as f:
            registry = json.load(f)
    ts = datetime.now().isoformat(timespec="seconds")
    ref = fields.get("certificate_no", {}).get("value")
    base = {"source": "MOCK-ISSUER-REGISTRY", "timestamp": ts, "reference": ref, "attempt": attempt}
    if not ref:
        pid, aid = (fields.get("permanent_id") or {}).get("value"), (fields.get("application_id") or {}).get("value")
        if pid or aid:    # AICTE EoA: identified by Permanent / Application ID, not a certificate number
            return {**base, "reference": aid or pid, "status": "manual_review_required",
                    "detail": f"EoA has no certificate number. Check Permanent ID {pid or '-'} / Application ID {aid or '-'} on the AICTE portal (not connected in this prototype)"}
        return {**base, "status": "manual_review_required", "detail": "No reference number extracted"}
    if ref.startswith("UNAVAIL") or (ref.startswith("FLAKY") and attempt < 2):
        return {**base, "status": "source_unavailable", "detail": "Issuer service could not be reached"}
    if ref.startswith("PENDING"):
        return {**base, "status": "pending", "detail": "Issuer has not responded yet"}
    rec = registry.get(ref)
    if not rec:
        return {**base, "status": "manual_review_required", "detail": "Reference not found in source"}
    diffs = []
    iid = fields.get("institution_id", {}).get("value")
    if iid and iid != rec["institution_id"]:
        diffs.append(f"institution_id: submitted {iid} vs source {rec['institution_id']}")
    vu = fields.get("valid_until", {}).get("value")
    if vu and rec.get("valid_until") and vu != rec["valid_until"]:
        diffs.append(f"valid_until: submitted {vu} vs source {rec['valid_until']}")
    if diffs:
        return {**base, "status": "mismatch_detected", "detail": "; ".join(diffs)}
    if rec.get("valid_until") and _parse(rec["valid_until"]) < eval_date.date():
        return {**base, "status": "expired", "detail": f"Source says valid until {rec['valid_until']}"}
    return {**base, "status": "verified", "detail": "Source confirms record and fields match"}
