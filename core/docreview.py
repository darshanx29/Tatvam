"""What the officer sees for each uploaded document: every extracted value listed, each marked
Found / Missing / Expired / Mismatch / Not verified / Check, built from the extracted fields, the rule results
and the source-verification answer. Pure functions - no Flask / OCR imports."""
from .eoa import EOA_FIELDS, looks_like_eoa

LABELS = {"institution_name": "Institution name", "institution_id": "Institution ID", "certificate_no": "Certificate / reference no.",
          "issued_by": "Issued by", "issue_date": "Issue date", "valid_until": "Valid until", "academic_year": "Academic year",
          "programme": "Programme", "approved_intake": "Approved intake", "signatory": "Signatory",
          "accreditation_body": "Accreditation body", "grade": "Grade", "facility": "Facility",
          "permanent_id": "Permanent ID", "application_id": "Application ID", "region": "Region",
          "institution_type": "Institution type", "establishment_year": "Establishment year", "approval_date": "Approval date"}
_COMMON = ["institution_name", "institution_id", "certificate_no", "issued_by", "issue_date", "valid_until"]
EXPECTED = {"accreditation_certificate": _COMMON, "noc": _COMMON, "infrastructure_certificate": _COMMON,
            "affidavit": ["institution_name", "institution_id", "certificate_no", "issued_by", "issue_date"],
            "approval_record": _COMMON}                     # an AICTE EoA letter uses EOA_FIELDS instead
DOC_TITLES = {"approval_record": "Extension of Approval / approval record", "accreditation_certificate": "Accreditation certificate",
              "noc": "No Objection Certificate (NOC)", "affidavit": "Affidavit / undertaking",
              "infrastructure_certificate": "Infrastructure certificate", "floor_plan": "Floor plan",
              "infrastructure_photo": "Infrastructure photo", "unknown": "Unrecognised document"}
RANK = {"ok": 0, "warn": 1, "bad": 2}
PRI = {"Found": 0, "Verified": 0, "Identified": 0, "Check": 1, "Not verified": 1, "Mismatch": 2, "Missing": 3, "Expired": 3}
_VERIF = {"verified": ("Verified", "ok"), "mismatch_detected": ("Mismatch", "bad"), "expired": ("Expired", "bad"),
          "manual_review_required": ("Not verified", "warn"), "source_unavailable": ("Not verified", "warn"), "pending": ("Not verified", "warn")}


def _mark(row, status, level, note=""):
    """Keep the most severe status on a row; collect every note."""
    if note and note not in row["note"]:
        row["note"] = (row["note"] + " | " if row["note"] else "") + note
    if PRI.get(status, 1) >= PRI.get(row["status"], 1):
        row["status"], row["level"] = status, level


def _keys_for(item):
    """Which extracted field(s) a rule result is about."""
    t, reason = item.get("rule_type"), str(item.get("reason", ""))
    if t == "not_expired": return ["valid_until"]
    if t == "academic_year_valid": return ["academic_year"]
    if t == "match_app_field": return ["institution_id"]
    if t == "date_order": return ["issue_date", "valid_until"]
    if t == "match_record_name": return ["institution_name"]
    if t == "match_record_intake": return ["approved_intake", "programme"]
    if t == "has_identifier": return ["certificate_no"]
    if t == "cross_doc_consistent": return [reason.split(" differs")[0]] if " differs" in reason else []
    return []


def review(doc_type, fields, assessment=(), verification=None, anomalies=()):
    """fields: {name: {value, confidence}}; assessment: rule results whose source is this document;
    verification: dict(status, detail, reference) or None; anomalies: [{reason}] for this document."""
    eoa = doc_type == "approval_record" and (looks_like_eoa(fields) or "certificate_no" not in fields)
    expected = [k for _, k in EOA_FIELDS] if eoa else EXPECTED.get(doc_type, [])
    order = expected + [k for k in fields if k not in expected]
    rows, by = [], {}
    for k in order:
        f = fields.get(k)
        has = bool(f and str(f.get("value", "")).strip())
        if not has and k not in expected:
            continue
        row = {"key": k, "label": LABELS.get(k, k.replace("_", " ").capitalize()), "value": f["value"] if has else None,
               "conf": f.get("confidence") if has else None, "status": "Found" if has else "Missing",
               "level": "ok" if has else "bad", "note": "" if has else "Not found on the document - check the original"}
        if has and row["conf"] is not None and row["conf"] < 0.8:
            _mark(row, "Check", "warn", "Low OCR confidence - compare with the original")
        rows.append(row); by[k] = row

    shown, extra = set(), []
    for it in assessment:
        if it.get("status") not in ("FAIL", "INCONCLUSIVE"):
            continue
        keys = [k for k in _keys_for(it) if k in by]
        reason = str(it.get("reason") or it.get("observed") or "")
        if not keys:
            extra.append({"level": "bad" if it["status"] == "FAIL" else "warn", "text": f"{it.get('title')}: {reason}"})
            continue
        for k in keys:
            row = by[k]
            if it["status"] == "INCONCLUSIVE":
                _mark(row, "Check", "warn", f"{reason} ({it.get('observed')})")
            elif reason.startswith("Expired"):
                _mark(row, "Expired", "bad", reason)
            elif row["status"] != "Missing":
                _mark(row, "Mismatch", "bad", str(it.get("observed")) if it.get("rule_type") == "date_order"
                      else f"{reason}: document has {it.get('observed')}, expected {it.get('expected')}")
    for a in anomalies:
        extra.append({"level": "warn", "text": f"Anomaly: {a.get('reason')}"})

    if verification:                                    # source verification (issuer registry / AICTE record)
        label, level = _VERIF.get(verification.get("status"), ("Not verified", "warn"))
        detail = verification.get("detail") or ""
        if "certificate_no" in by and by["certificate_no"]["value"] and label != "Verified":
            _mark(by["certificate_no"], label, level, detail)
        rows.append({"key": "source_verification", "label": "Source verification", "value": verification.get("reference") or "-",
                     "conf": None, "status": label, "level": level, "note": detail})
    if not any(r["value"] for r in rows if r["key"] != "source_verification") and doc_type not in ("floor_plan", "infrastructure_photo"):
        extra.append({"level": "bad", "text": "No fields could be read from this document. Open the viewer to see the text, or request a clearer copy."})

    body = [r for r in rows if r["key"] != "source_verification"]
    src = next((r for r in rows if r["key"] == "source_verification"), None)

    def n(st):                     # count each problem once (the source-verification row repeats the certificate row)
        c = sum(1 for r in body if r["status"] == st)
        return c or (1 if src and src["status"] == st else 0)
    plural = {"Expired": "expired", "Mismatch": "mismatch", "Missing": "missing"}
    parts = [f"{n(k)} {v}" + ("es" if k == "Mismatch" and n(k) > 1 else "") for k, v in plural.items() if n(k)]
    level = "bad" if parts or any(a["level"] == "bad" for a in extra) else ("warn" if extra or any(r["level"] == "warn" for r in rows) else "ok")
    headline = " · ".join(parts) if parts else ("Needs officer attention" if level != "ok" else "All checks passed")
    return {"title": DOC_TITLES.get(doc_type, doc_type), "headline": headline, "level": level, "rows": rows, "alerts": extra}
