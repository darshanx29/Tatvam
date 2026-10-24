"""Deterministic, versioned, configurable rule engine. Output = evidence-linked results.
Every rule yields PASS / FAIL / INCONCLUSIVE (or NOT_APPLICABLE). Findings = FAIL + INCONCLUSIVE."""
import json, os, re
from datetime import datetime, date

from . import eoa

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")
TYPES = ("required_doc", "required_field", "not_expired", "match_app_field", "date_order", "low_confidence",
         "unreadable_doc", "unknown_doc", "cross_doc_consistent", "has_identifier", "match_record_intake",
         "match_record_name", "app_programme_in_record", "infra_quality", "academic_year_valid")
SEVERITIES = ("low", "medium", "high")
INFRA_TYPES = ("infrastructure_photo", "floor_plan")


def load_rules(path=RULES_PATH):
    with open(path) as f:
        return json.load(f)


def _d(s):
    """dd-mm-yyyy (or /) -> date, None when unparseable."""
    try:
        return datetime.strptime(str(s).replace("/", "-"), "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None


def _iso(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _on(eval_date):
    return eval_date.date() if isinstance(eval_date, datetime) else eval_date


# ----------------------------------------------------------------- versions & applicability
def validate_definition(r):
    """Returns a list of problems (empty = valid)."""
    p = []
    for k in ("id", "version", "title", "type", "categories", "severity", "remedy"):
        if not r.get(k):
            p.append(f"missing '{k}'")
    if r.get("type") and r["type"] not in TYPES:
        p.append(f"unknown type '{r['type']}'")
    if r.get("severity") and r["severity"] not in SEVERITIES:
        p.append("severity must be low, medium or high")
    if r.get("categories") is not None and not isinstance(r.get("categories"), list):
        p.append("categories must be a list")
    for k in ("effective_from", "effective_to"):
        try: _iso(r.get(k))
        except ValueError: p.append(f"{k} must be YYYY-MM-DD")
    if r.get("applies_when") is not None and not isinstance(r["applies_when"], dict):
        p.append("applies_when must be an object")
    t = r.get("type")
    if t == "required_doc" and not r.get("doc_type"): p.append("required_doc needs doc_type")
    if t in ("not_expired", "match_app_field") and not r.get("field"): p.append(f"{t} needs field")
    if t == "low_confidence" and not isinstance(r.get("threshold"), (int, float)): p.append("low_confidence needs numeric threshold")
    if t == "required_field" and not (r.get("doc_types") and r.get("fields")): p.append("required_field needs doc_types and fields")
    if t == "has_identifier" and not r.get("doc_types"): p.append("has_identifier needs doc_types")
    if t == "academic_year_valid" and not (r.get("doc_types") and r.get("field")): p.append("academic_year_valid needs doc_types and field")
    if t == "cross_doc_consistent" and not r.get("fields"): p.append("cross_doc_consistent needs fields")
    return p


def _ver(v):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"\.", str(v)))


def select_versions(versions, eval_date):
    """versions: list of rule dicts (many versions per id). Picks, per rule id, the version in force on
    eval_date; an inactive version switches the rule off."""
    on, best = _on(eval_date), {}
    for r in versions:
        f, t = _iso(r.get("effective_from")), _iso(r.get("effective_to"))
        if (f and on < f) or (t and on > t):
            continue
        key = (f or date.min, _ver(r["version"]))
        if r["id"] not in best or key > best[r["id"]][0]:
            best[r["id"]] = (key, r)
    return [r for _, r in best.values() if r.get("active", True)]


def applies(rule, app):
    if app["category"] not in rule["categories"]:
        return False
    for k, allowed in (rule.get("applies_when") or {}).items():
        if app.get(k) not in allowed:
            return False
    return True


# ----------------------------------------------------------------- evaluation
def _res(rule, status, observed, expected, source, reason=""):
    return {"rule_id": rule["id"], "rule_version": rule["version"], "title": rule["title"], "status": status,
            "severity": rule["severity"], "observed": observed, "expected": expected, "source": source,
            "reason": reason, "clause": rule.get("clause"), "next_step": rule["remedy"], "rule_type": rule["type"]}


def _norm(v):
    return re.sub(r"\s+", " ", str(v)).strip().lower()


def _per_doc(rule, docs, test, pass_text):
    """Run test(doc)->None(pass) | (status, observed, expected, reason) over applicable docs."""
    out, seen = [], 0
    for d in docs:
        r = test(d)
        if r is False:          # not applicable to this doc
            continue
        seen += 1
        if r:
            out.append(_res(rule, r[0], r[1], r[2], d["name"], r[3]))
    if not out:
        return [_res(rule, "PASS" if seen else "NOT_APPLICABLE", pass_text if seen else "no applicable document", "-", "all documents")]
    return out


def evaluate_rule(r, app, docs, eval_date, record=None):
    t, on = r["type"], _on(eval_date)
    if t == "required_doc":
        ok = any(d["doc_type"] == r["doc_type"] for d in docs)
        return [_res(r, "PASS" if ok else "FAIL", "uploaded" if ok else "not uploaded", r["doc_type"], "checklist")]

    if t == "required_field":
        def test(d):
            if d["doc_type"] not in r["doc_types"]: return False
            if r.get("only_if") == "eoa_letter" and not eoa.looks_like_eoa(d["fields"], d.get("text", "")): return False
            miss = [f for f in r["fields"] if not (d["fields"].get(f) or {}).get("value", "").strip()]
            return ("FAIL", f"blank/missing: {miss}", "all mandatory fields present", "Mandatory field blank") if miss else None
        return _per_doc(r, docs, test, "mandatory fields present")

    if t == "not_expired":
        def test(d):
            if r["field"] not in d["fields"]: return False
            v = d["fields"][r["field"]]["value"]; dv = _d(v)
            if dv is None: return ("INCONCLUSIVE", v, "dd-mm-yyyy date", "Date could not be parsed")
            return ("FAIL", v, f"on/after {on:%d-%m-%Y}", f"Expired on {v}") if dv < on else None
        return _per_doc(r, docs, test, f"valid on {on:%d-%m-%Y}")

    if t == "match_app_field":
        def test(d):
            if r["field"] not in d["fields"]: return False
            v = d["fields"][r["field"]]["value"]
            return ("FAIL", v, app[r["field"]], "Identifier differs from application record") if v != app[r["field"]] else None
        return _per_doc(r, docs, test, "matches application")

    if t == "academic_year_valid":
        def test(d):
            if d["doc_type"] not in r["doc_types"] or r["field"] not in d["fields"]: return False
            v = d["fields"][r["field"]]["value"]
            end = eoa.academic_year_end(v, r.get("ends_on", "30-06"))
            if end is None: return ("INCONCLUSIVE", v, "academic year such as 2025-26", "Academic year could not be parsed")
            return ("FAIL", v, f"academic year ending on/after {on:%d-%m-%Y}", f"Expired: academic year {v} ended on {end:%d-%m-%Y}") if end < on else None
        return _per_doc(r, docs, test, f"academic year current on {on:%d-%m-%Y}")

    if t == "date_order":
        def test(d):
            F = d["fields"]
            if "issue_date" not in F or "valid_until" not in F: return False
            a, b = _d(F["issue_date"]["value"]), _d(F["valid_until"]["value"])
            if a is None or b is None: return ("INCONCLUSIVE", "unparseable date", "issue_date <= valid_until", "Date could not be parsed")
            return ("FAIL", f"issue {F['issue_date']['value']} > valid {F['valid_until']['value']}", "issue_date <= valid_until", "") if a > b else None
        return _per_doc(r, docs, test, "dates consistent")

    if t == "low_confidence":
        def test(d):
            low = [k for k, v in d["fields"].items() if v["confidence"] < r["threshold"]]
            if d["fields"] == {}: return False
            return ("INCONCLUSIVE", f"low confidence: {low}", f">= {r['threshold']}", "Officer to confirm extracted values") if low else None
        return _per_doc(r, docs, test, "extraction confidence adequate")

    if t == "unreadable_doc":
        return _per_doc(r, docs, lambda d: False if d["doc_type"] in INFRA_TYPES else (("INCONCLUSIVE", "no readable text", "legible document", "Unreadable scan") if d["ocr_method"] == "unreadable" else None), "all documents readable")

    if t == "unknown_doc":
        return _per_doc(r, docs, lambda d: ("INCONCLUSIVE", "type not recognised", "supported document type", "Classification found no keywords") if d["doc_type"] == "unknown" and d["ocr_method"] != "unreadable" else None, "all documents classified")

    if t == "has_identifier":
        return _per_doc(r, docs, lambda d: False if d["doc_type"] not in r["doc_types"] else (None if (d["fields"].get("certificate_no") or {}).get("value") or (d["doc_type"] == "approval_record" and any((d["fields"].get(k) or {}).get("value") for k in ("application_id", "permanent_id"))) else ("FAIL", "no certificate/reference number", "identifier present", "Evidence lacks an expected identifier")), "identifier present")

    if t == "cross_doc_consistent":
        out = []
        for f in r["fields"]:
            vals = {}
            for d in docs:
                if f in d["fields"]:
                    vals.setdefault(_norm(d["fields"][f]["value"]), []).append((d["name"], d["fields"][f]["value"]))
            if len(vals) > 1:
                detail = "; ".join(f"{n}={v}" for g in vals.values() for n, v in g)
                out.append(_res(r, "FAIL", detail, f"same {f} in every document", ", ".join(n for g in vals.values() for n, _ in g), f"{f} differs across documents"))
        return out or [_res(r, "PASS", "consistent", "-", "all documents")]

    if t == "match_record_name":
        if not record: return [_res(r, "INCONCLUSIVE", "no authorized record", "record available", "institution record", "Institutional record unavailable")]
        return _per_doc(r, docs, lambda d: False if "institution_name" not in d["fields"] else (None if _norm(d["fields"]["institution_name"]["value"]) == _norm(record["name"]) else ("FAIL", d["fields"]["institution_name"]["value"], record["name"], "Name differs from authorized record")), "matches authorized record")

    if t == "app_programme_in_record":
        if not app.get("programme"): return [_res(r, "NOT_APPLICABLE", "no programme on application", "-", "application")]
        if not record: return [_res(r, "INCONCLUSIVE", "no authorized record", "record available", "institution record", "Institutional record unavailable")]
        ok = app["programme"] in record["programmes"]
        return [_res(r, "PASS" if ok else "FAIL", app["programme"], ", ".join(record["programmes"]) or "-", "application", "" if ok else "Programme not in authorized record")]

    if t == "match_record_intake":
        if not record: return [_res(r, "INCONCLUSIVE", "no authorized record", "record available", "institution record", "Institutional record unavailable")]
        def test(d):
            if d["doc_type"] != "approval_record": return False
            F = d["fields"]
            prog, intake = (F.get("programme") or {}).get("value"), (F.get("approved_intake") or {}).get("value")
            if not intake: return ("INCONCLUSIVE", "intake not extracted", "approved intake", "Cannot compare")
            prog = prog or app.get("programme") or (next(iter(record["programmes"])) if len(record["programmes"]) == 1 else None)
            if prog not in record["programmes"]: return ("FAIL", f"{prog}", ", ".join(record["programmes"]), "Programme not in authorized record")
            exp = str(record["programmes"][prog])
            return ("FAIL", f"{prog}: intake {intake}", f"intake {exp}", "Intake differs from authorized record") if intake != exp else None
        return _per_doc(r, docs, test, "programme and intake match authorized record")

    if t == "infra_quality":
        def test(d):
            if d["doc_type"] not in INFRA_TYPES: return False
            q = d.get("quality")
            if q is None: return False
            return ("INCONCLUSIVE", "; ".join(q["issues"]), "usable evidence", "Advisory: refer for additional evidence or inspection") if q["issues"] else None
        return _per_doc(r, docs, test, "evidence quality adequate (advisory; physical compliance not established)")
    return []


def assess(app, docs, eval_date, rules=None, record=None):
    """All applicable rule results incl. PASS (drives the compliance screen)."""
    out = []
    for r in (rules if rules is not None else load_rules()):
        if applies(r, app):
            out.extend(evaluate_rule(r, app, docs, eval_date, record))
    return out


def validate(app, docs, eval_date, rules=None, record=None):
    """Findings only: FAIL and INCONCLUSIVE results."""
    return [x for x in assess(app, docs, eval_date, rules, record) if x["status"] in ("FAIL", "INCONCLUSIVE")]
