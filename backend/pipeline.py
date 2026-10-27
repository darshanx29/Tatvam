"""End-to-end run for one application folder:  python pipeline.py data/synthetic/APP-001 EoA 1-1001"""
import os, sys, json
from datetime import datetime
from core import extractor, anomaly, mock_issuer, rules_engine, records, infra, security

EVAL_DATE = datetime(2026, 10, 22)  # default evaluation date used for expiry rules
VERIFIABLE = ("accreditation_certificate", "noc", "infrastructure_certificate", "approval_record")
NOTE_PRELIM = "Preliminary indicator - needs human review"
NOTE_LEGIT = "Preliminary indicator - may have legitimate explanation (scanning, recompression, conversion)"


def process(folder, category, institution_id, eval_date=EVAL_DATE, rules=None, record="auto", overrides=None,
            progress=None, app_extra=None, other_docs=None, qr_hosts=(), attempts=None, registry=None):
    """folder: directory of (decrypted) files. overrides: {(filename, field): corrected value}.
    other_docs: [{app_id, name, sha, phashes}] from OTHER applications (cross-application duplicates)."""
    progress = progress or (lambda pct, msg: None)
    overrides, attempts, other_docs = overrides or {}, attempts or {}, other_docs or []
    app = {"category": category, "institution_id": institution_id, **(app_extra or {})}
    if record == "auto":
        record = records.get_record(institution_id)
    files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(extractor.SUPPORTED_EXT)]

    docs = []
    for i, fn in enumerate(files):
        progress(5 + int(55 * i / max(len(files), 1)), f"Reading {fn}")
        path = os.path.join(folder, fn)
        ex = extractor.extract_pages(path)
        text = "\n".join(p["text"] for p in ex["pages"])
        dtype, cconf = extractor.classify(text, fn)
        fields = extractor.extract_fields(ex["pages"], ex["method"])
        for (ofn, fld), val in overrides.items():        # authorized corrections survive re-runs
            if ofn == fn:
                old = fields.get(fld, {})
                fields[fld] = {"value": val, "confidence": 1.0, "page": old.get("page", 1), "bbox": old.get("bbox"),
                               "pw": old.get("pw"), "ph": old.get("ph"), "corrected": True, "ocr_value": old.get("value")}
        d = {"name": fn, "path": path, "doc_type": dtype, "class_conf": cconf, "ocr_method": ex["method"],
             "mean_conf": ex["mean_conf"], "text": text, "fields": fields, "sha": anomaly.sha256(path),
             "size": os.path.getsize(path), "quality": None, "qr": []}
        try:
            d["phashes"] = anomaly.page_hashes(path)
        except Exception:
            d["phashes"] = []
        if dtype in rules_engine.INFRA_TYPES:
            try: d["quality"] = infra.image_quality(path) if fn.lower().endswith(extractor.IMAGE_EXT) else None
            except Exception: d["quality"] = None
        docs.append(d)

    progress(65, "Running validation rules")
    applied = rules if rules is not None else rules_engine.load_rules()
    assessment = rules_engine.assess(app, docs, eval_date, applied, record)
    findings = [x for x in assessment if x["status"] in ("FAIL", "INCONCLUSIVE")]

    progress(75, "Anomaly analysis")
    anomalies = []
    for a, b, why in anomaly.duplicate_flags(docs):
        anomalies.append({"type": "duplicate", "evidence": [a, b], "reason": why, "note": NOTE_PRELIM})
    for d in docs:
        cert = (d["fields"].get("certificate_no") or {}).get("value")
        for o in other_docs:
            if o.get("institution_id") == institution_id:
                continue                          # an institution re-submitting its own file is normal
            if o["sha"] == d["sha"]:
                anomalies.append({"type": "duplicate_cross", "evidence": [d["name"]], "private": f"identical file in {o['app_id']}/{o['name']}",
                                  "reason": "Identical file already submitted by another institution", "note": NOTE_PRELIM})
                break
            if cert and o.get("cert_no") == cert:
                anomalies.append({"type": "duplicate_cross", "evidence": [d["name"]], "private": f"same certificate number as {o['app_id']}/{o['name']}",
                                  "reason": f"Certificate/reference number {cert} also appears in another institution's application", "note": NOTE_PRELIM})
                break
        for why in anomaly.metadata_flags(d["path"]):
            anomalies.append({"type": "metadata", "evidence": [d["name"]], "reason": why, "note": NOTE_LEGIT})
        for why in anomaly.structure_flags(d["path"]):
            anomalies.append({"type": "structure", "evidence": [d["name"]], "reason": why, "note": NOTE_LEGIT})
        st, detail = anomaly.signature_status(d["path"])
        d["signature"] = st
        if st in ("invalid", "present_unvalidated"):
            anomalies.append({"type": "signature", "evidence": [d["name"]], "reason": detail,
                              "note": "Signature could not be confirmed - route to manual verification"})
        try:
            for url in anomaly.qr_payloads(d["path"]):
                if url.lower().startswith(("http://", "https://")):
                    ok = security.host_allowed(url, qr_hosts)
                    d["qr"].append({"url": url, "authorized_host": ok})
                    if not ok:
                        anomalies.append({"type": "qr", "evidence": [d["name"]], "reason": f"QR destination not authenticated: {url[:80]}",
                                          "note": "Not fetched; host is not on the authorized allow-list"})
        except Exception:
            pass
        v = anomaly.ela_flag(d["path"])
        if v:
            anomalies.append({"type": "visual", "evidence": [d["name"]], "reason": v["reason"], "bbox": v["bbox"], "note": NOTE_LEGIT})

    progress(88, "Source verification")
    verifications = []
    for d in docs:
        if d["doc_type"] in VERIFIABLE:
            verifications.append({"document": d["name"], **mock_issuer.verify(d["fields"], eval_date, registry=registry,
                                                                              attempt=attempts.get(d["name"], 1))})

    open_items = len(findings) + len(anomalies) + sum(v["status"] != "verified" for v in verifications)
    progress(100, "Done")
    return {"application": app, "evaluated_on": f"{eval_date:%d-%m-%Y}",
            "status": "OFFICER_REVIEW" if open_items else "PRELIMINARY_PASS",
            "rules_used": sorted({f"{r['id']}@{r['version']}" for r in applied if rules_engine.applies(r, app)}),
            "documents": [{k: v for k, v in d.items() if k not in ("text", "phashes", "path")} for d in docs],
            "_docs": docs,        # in-memory only (hashes/text) - stripped before persisting
            "assessment": assessment, "findings": findings, "anomalies": anomalies, "verifications": verifications,
            "disclaimer": "Decision-support only. No automatic adverse regulatory action."}


if __name__ == "__main__":
    folder, cat, iid = sys.argv[1], sys.argv[2], sys.argv[3]
    rep = process(folder, cat, iid)
    rep.pop("_docs")
    print(json.dumps(rep, indent=2, default=str))
