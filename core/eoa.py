"""AICTE Extension of Approval (EoA) helpers shared by the extractor, rules engine and UI (no heavy imports)."""
import re

# (label shown to the officer, extracted-field name) in display order
EOA_FIELDS = [("Institution", "institution_name"), ("Permanent ID", "permanent_id"), ("Application ID", "application_id"),
              ("Region", "region"), ("Institution type", "institution_type"), ("Establishment year", "establishment_year"),
              ("Approval date", "approval_date"), ("Academic year", "academic_year")]
EOA_ONLY = ("permanent_id", "application_id", "region", "institution_type", "establishment_year", "approval_date")
EOA_TEXT = re.compile(r"extension\s+of\s+approval\s*\(\s*eoa\s*\)|permanent\s*i\.?d|application\s*i\.?d", re.I)


def looks_like_eoa(fields, text=""):
    """True for a real AICTE EoA letter (as opposed to the older 'approval record' format)."""
    return any(k in fields for k in EOA_ONLY) or bool(EOA_TEXT.search(text or ""))


def academic_year_end(value, ends_on="30-06"):
    """'2025-26' / '2025–2026' -> date the academic year ends (default 30 June of the second year). None if unparseable."""
    from datetime import date
    m = re.search(r"(\d{4})\s*[-\u2013\u2014/]\s*(\d{2,4})", str(value))
    if not m:
        return None
    y1, y2 = int(m.group(1)), m.group(2)
    y2 = int(y2) if len(y2) == 4 else (y1 // 100) * 100 + int(y2)
    try:
        dd, mm = (int(x) for x in str(ends_on).split("-"))
        return date(y2, mm, dd)
    except (ValueError, TypeError):
        return None
