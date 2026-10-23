"""Measure OCR / rule / anomaly / verification quality on the LABELLED SYNTHETIC set and write data/eval_report.json.
python evaluate.py        -> prints the report; the dashboard reads the saved JSON.
Ground truth below is written by hand from what the synthetic generator planted - NOT taken from system output.
These numbers describe synthetic data only; they are not real-world accuracy claims."""
import json, os, statistics, sys, time
from datetime import datetime
import pipeline

BASE = os.path.dirname(os.path.abspath(__file__))
EVAL_DATE = datetime(2026, 10, 22)
IS = lambda *a: a


def F(name, iid, ref, issuer, issue, valid, **extra):
    return {"institution_name": name, "institution_id": iid, "certificate_no": ref, "issued_by": issuer, "issue_date": issue, "valid_until": valid, **extra}


D1, N2, N3 = "Demo Institute of Technology", "Sample College of Engineering", "Scan Test Institute"
TRUTH = {
    "APP-001": {"institution_id": "1-1001", "programme": "B.Tech Computer Engineering", "docs": {
        "accreditation.pdf": F(D1, "1-1001", "ACC-2026-001", "NBA", "01-01-2026", "31-12-2028"),
        "noc.pdf": F(D1, "1-1001", "NOC-MH-777", "State Govt", "10-02-2026", "31-12-2027"),
        "affidavit.pdf": F(D1, "1-1001", "AFF-55", "Notary", "05-03-2026", "31-12-2027"),
        "approval_record.pdf": F(D1, "1-1001", "EOA-2025-9", "AICTE", "01-06-2025", "31-05-2027", programme="B.Tech Computer Engineering", approved_intake="120"),
        "infra_fire.pdf": F(D1, "1-1001", "INF-FIRE-12", "Fire Dept", "15-01-2026", "14-01-2027")},
        "findings": [], "anomalies": [],
        "verification": {"accreditation.pdf": "verified", "noc.pdf": "verified", "approval_record.pdf": "verified", "infra_fire.pdf": "verified"}},
    "APP-002": {"institution_id": "1-2002", "programme": None, "docs": {
        "accreditation.pdf": F(N2, "1-2002", "ACC-2024-002", "NAAC", "01-07-2021", "30-06-2026"),
        "noc.pdf": F(N2, "1-2999", "NOC-MH-888", "State Govt", "10-02-2026", "31-12-2027"),
        "noc_copy.pdf": F(N2, "1-2999", "NOC-MH-888", "State Govt", "10-02-2026", "31-12-2027"),
        "approval_record.pdf": F(N2, "1-2002", "EOA-2025-4", "AICTE", "10-05-2026", "01-01-2026", programme="B.Tech Mechanical Engineering", approved_intake="60"),
        "infra_fire.pdf": F(N2, "1-2002", "UNAVAIL-INF-3", "Fire Dept", "15-01-2026", "14-01-2027")},
        "findings": [("R-DOC-AFF", "checklist"), ("R-EXP-01", "accreditation.pdf"), ("R-EXP-01", "approval_record.pdf"), ("R-ID-01", "noc.pdf"), ("R-ID-01", "noc_copy.pdf"),
                     ("R-DATE-01", "approval_record.pdf"), ("R-XDOC-01", "multi"), ("R-REC-03", "approval_record.pdf"),
                     ("VER-EXPIRED", "accreditation.pdf"), ("VER-EXPIRED", "approval_record.pdf"), ("VER-SOURCE_UNAVAILABLE", "infra_fire.pdf"),
                     ("VER-MISMATCH_DETECTED", "noc.pdf"), ("VER-MISMATCH_DETECTED", "noc_copy.pdf")],
        "anomalies": [("ANOM-DUPLICATE", "multi"), ("ANOM-METADATA", "infra_fire.pdf")],
        "verification": {"accreditation.pdf": "expired", "noc.pdf": "mismatch_detected", "noc_copy.pdf": "mismatch_detected", "approval_record.pdf": "expired", "infra_fire.pdf": "source_unavailable"}},
    "APP-003": {"institution_id": "1-3003", "programme": "B.Tech Civil Engineering", "docs": {
        "accreditation.png": F(N3, "1-3003", "ACC-2026-031", "NBA", "01-01-2026", "31-12-2028"),
        "noc.png": F(N3, "1-3003", "NOC-MH-031", "State Govt", "10-02-2026", "31-12-2027"),
        "affidavit.png": F(N3, "1-3003", "AFF-031", "Notary", "05-03-2026", "31-12-2027"),
        "approval_record.png": F(N3, "1-3003", "EOA-2025-31", "AICTE", "01-06-2025", "31-05-2027", programme="B.Tech Civil Engineering", approved_intake="60"),
        "infra_fire.png": F(N3, "1-3003", "INF-FIRE-31", "Fire Dept", "15-01-2026", "14-01-2027")},
        "findings": [("R-INFRA-01", "lab_photo.jpg")], "anomalies": [],
        "verification": {"accreditation.png": "verified", "noc.png": "verified", "approval_record.png": "verified", "infra_fire.png": "verified"}},
    "APP-004": {"institution_id": "1-3003", "programme": "B.Tech Civil Engineering", "docs": {
        "accreditation.jpg": F(N3, "1-3003", "ACC-2026-041", "NBA", "01-01-2026", "31-12-2028")},
        "findings": [("R-DOC-NOC", "checklist"), ("R-DOC-AFF", "checklist"), ("R-DOC-APR", "checklist"), ("R-DOC-INF", "checklist")], "anomalies": [],
        "verification": {"accreditation.jpg": "verified"}},
}


def key(rule_id, source):
    return (rule_id, "multi" if "," in source else source)


def ratio(a, b):
    return round(a / b, 3) if b else None


def run():
    ocr = {"correct": 0, "extracted": 0, "expected": 0, "by_method": {}}
    tp = fp = fn = tn = 0
    atp = afp = afn = 0
    vok = vtot = 0
    times, n_docs = [], 0
    for app, t in TRUTH.items():
        t0 = time.time()
        rep = pipeline.process(os.path.join(BASE, "data", "synthetic", app), "EoA", t["institution_id"], eval_date=EVAL_DATE,
                               app_extra={"programme": t["programme"]})
        times.append(time.time() - t0)
        docs = {d["name"]: d for d in rep["documents"]}
        for name, exp in t["docs"].items():
            n_docs += 1
            got = docs.get(name, {}).get("fields", {})
            m = docs.get(name, {}).get("ocr_method", "missing")
            bm = ocr["by_method"].setdefault(m, {"correct": 0, "expected": 0})
            for fld, val in exp.items():
                ocr["expected"] += 1; bm["expected"] += 1
                if fld in got:
                    ocr["extracted"] += 1
                    if got[fld]["value"] == val:
                        ocr["correct"] += 1; bm["correct"] += 1
        # rule + verification findings
        expected = {(r, s) for r, s in t["findings"]}
        predicted = {key(f["rule_id"], f["source"]) for f in rep["findings"]}
        for v in rep["verifications"]:
            if v["status"] != "verified":
                predicted.add(("VER-" + v["status"].upper(), v["document"]))
        universe = {key(x["rule_id"], x["source"]) for x in rep["assessment"]} | {("VER-OK", d["name"]) for d in rep["documents"]} | expected | predicted
        tp += len(expected & predicted); fp += len(predicted - expected); fn += len(expected - predicted)
        tn += len(universe - expected - predicted)
        # anomalies
        ea = {(r, s) for r, s in t["anomalies"]}
        pa = {("ANOM-" + a["type"].upper(), "multi" if len(a["evidence"]) > 1 else a["evidence"][0]) for a in rep["anomalies"]}
        atp += len(ea & pa); afp += len(pa - ea); afn += len(ea - pa)
        # verification statuses
        got_v = {v["document"]: v["status"] for v in rep["verifications"]}
        for d, st in t["verification"].items():
            vtot += 1; vok += got_v.get(d) == st
    return {
        "generated_at": datetime.now().strftime("%d-%m-%Y %H:%M"), "n_applications": len(TRUTH), "n_documents": n_docs,
        "caveat": "Measured on a small labelled SYNTHETIC set (clean generated documents). Real scans, handwriting and genuine forgeries will perform differently.",
        "ocr": {"exact_match": ratio(ocr["correct"], ocr["expected"]), "precision": ratio(ocr["correct"], ocr["extracted"]), "recall": ratio(ocr["extracted"], ocr["expected"]),
                "by_method": {m: {"exact_match": ratio(v["correct"], v["expected"]), "fields": v["expected"]} for m, v in ocr["by_method"].items()}},
        "findings": {"precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn), "false_positive_rate": ratio(fp, fp + tn), "tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "anomalies": {"precision": ratio(atp, atp + afp), "recall": ratio(atp, atp + afn), "tp": atp, "fp": afp, "fn": afn,
                      "note": "Visual-alteration (ELA) is experimental and excluded; no forgery label is ever asserted."},
        "verification": {"status_accuracy": ratio(vok, vtot)},
        "timing": {"mean_s": round(statistics.mean(times), 2), "p95_s": round(sorted(times)[min(len(times) - 1, int(round(0.95 * (len(times) - 1))))], 2)},
    }


if __name__ == "__main__":
    rep = run()
    with open(os.path.join(BASE, "data", "eval_report.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))
