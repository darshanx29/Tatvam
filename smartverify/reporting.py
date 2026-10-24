"""Validation report exports (JSON / CSV / PDF). Every export is audit-logged by the caller."""
import csv, io, json
from datetime import datetime

DISCLAIMER = ("AI findings are preliminary decision-support outputs. They are not official AICTE decisions; "
              "statutory scrutiny, inspection and final decisions rest with competent authorities. Synthetic/prototype data.")


def data(a, findings, acts, verifs, assessment, officer=False):
    return {"application": a.as_dict(), "generated_at": datetime.now().isoformat(timespec="seconds"),
            "rules_used": a.report.get("rules_used", []), "disclaimer": DISCLAIMER,
            "findings": [f.as_dict(officer) for f in findings], "verifications": verifs,
            "assessment": [{k: x[k] for k in ("rule_id", "rule_version", "title", "status", "severity", "observed", "expected", "source", "clause")} for x in assessment],
            "officer_actions": [{"actor": x.actor, "action": x.action, "reason": x.reason, "ts": x.ts.isoformat(timespec="seconds")} for x in acts],
            "recommendation": a.recommendation, "recommendation_note": a.recommendation_note}


def to_json(d):
    return json.dumps(d, indent=2, default=str)


def to_csv(d):
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["application", d["application"]["id"], "status", d["application"]["status"], "generated", d["generated_at"]])
    w.writerow([])
    w.writerow(["rule_id", "version", "kind", "severity", "title", "source", "observed", "expected", "reason", "next_step", "state"])
    for f in d["findings"]:
        w.writerow([f["rule_id"], f["rule_version"], f["kind"], f["severity"], f["title"], f["source"], f["observed"], f["expected"], f["reason"], f["next_step"], f["state"]])
    w.writerow([]); w.writerow(["disclaimer", d["disclaimer"]])
    return out.getvalue()


def to_pdf(d):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buf, st = io.BytesIO(), getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24, title=f"Validation report {d['application']['id']}")
    small = st["BodyText"].clone("small"); small.fontSize = 7.5; small.leading = 9
    P = lambda t: Paragraph(str(t or "-").replace("&", "&amp;").replace("<", "&lt;"), small)
    el = [Paragraph(f"AICTE Vidya-Niriksha - Validation report {d['application']['id']}", st["Title"]),
          Paragraph(f"Status: {d['application']['status']} | Category {d['application']['category']} | AY {d['application']['academic_year']} | Generated {d['generated_at']}", st["Normal"]),
          Paragraph("Rules used: " + ", ".join(d["rules_used"]), small), Spacer(1, 8), Paragraph("Findings", st["Heading2"])]
    rows = [["Rule", "Severity", "Finding", "Source", "Observed", "Expected", "Next step", "State"]] + \
           [[P(f"{f['rule_id']} v{f['rule_version']}"), P(f["severity"]), P(f["title"] + " - " + (f["reason"] or "")), P(f["source"]), P(f["observed"]), P(f["expected"]), P(f["next_step"]), P(f["state"])] for f in d["findings"]]
    def tbl(rows, widths):
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4eee3")), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 7.5)]))
        return t
    el.append(tbl(rows if len(rows) > 1 else rows + [[P("No open findings")] + [P("")] * 7], [70, 45, 170, 90, 120, 100, 100, 50]))
    el += [Spacer(1, 8), Paragraph("Source verification", st["Heading2"])]
    vr = [["Document", "Status", "Source", "Reference", "Detail", "When"]] + [[P(v["document"]), P(v["status"]), P(v["source"]), P(v["reference"]), P(v["detail"]), P(v["timestamp"])] for v in d["verifications"]]
    el.append(tbl(vr, [110, 90, 110, 90, 260, 80]))
    el += [Spacer(1, 8), Paragraph("Rule assessment (all executed checks)", st["Heading2"])]
    ar = [["Rule", "Result", "Observed", "Expected", "Source", "Clause"]] + [[P(f"{x['rule_id']} v{x['rule_version']}"), P(x["status"]), P(x["observed"]), P(x["expected"]), P(x["source"]), P(x["clause"])] for x in d["assessment"]]
    el.append(tbl(ar, [80, 70, 190, 150, 110, 140]))
    el += [Spacer(1, 8), Paragraph("Officer actions", st["Heading2"])]
    orr = [["When", "Actor", "Action", "Reason"]] + [[P(x["ts"]), P(x["actor"]), P(x["action"]), P(x["reason"])] for x in d["officer_actions"]]
    el.append(tbl(orr if len(orr) > 1 else orr + [[P("None"), P(""), P(""), P("")]], [110, 130, 90, 440]))
    el += [Spacer(1, 10), Paragraph("Recommendation: " + (d["recommendation"] or "not recorded"), st["Normal"]), Paragraph(d["disclaimer"], small)]
    doc.build(el)
    return buf.getvalue()
