"""OCR / text extraction, classification and field extraction for PDF, JPEG and PNG.
OCR output is extracted data, not verified truth -> every field carries confidence, page and location."""
import os, re
import pymupdf as fitz  # PyMuPDF

IMAGE_EXT = (".jpg", ".jpeg", ".png")
SUPPORTED_EXT = (".pdf",) + IMAGE_EXT

DOC_KEYWORDS = {
    "accreditation_certificate": ["accreditation", "naac", "nba", "grade"],
    "noc": ["no objection", "noc"],
    "affidavit": ["affidavit", "undertaking", "solemnly"],
    "approval_record": ["extension of approval", "approved intake", "eoa", "permanent id", "all india council for technical education"],
    "infrastructure_certificate": ["fire safety", "building stability", "infrastructure certificate"],
    "floor_plan": ["floor plan", "layout plan", "site plan"],
    "infrastructure_photo": ["laboratory", "classroom", "library photo", "campus photo"],
}
TITLE_BOOST = 3          # words in the first lines (the document title) count more
DATE = r"(\d{2}[-/]\d{2}[-/]\d{4})"
DATE_ANY = r"(\d{1,2}[-/ ](?:\d{2}|[A-Za-z]{3,9})[-/ ,]+\d{4})"      # 03-01-2025, 03-Jan-2025, 3 January 2025
SEP = r"\s*[:\-]?\s*"                                                # "Label: value", "Label - value" or value on the next line
# A pattern may be a string or a list of alternates (tried in order; first usable match wins).
FIELD_PATTERNS = {
    "institution_name": [r"Institution\s*Name\s*[:\-]\s*(.+)",
                         r"Name\s*of\s*the\s*(?:Institution|Institute)" + SEP + r"([^\n]+)",
                         r"Institute\s*Name" + SEP + r"([^\n]+)"],
    "institution_id":   r"Institution\s*ID\s*[:\-]\s*([\w\-]+)",
    "certificate_no":   r"(?:Certificate|Reference|Ref)\s*(?:No\.?|Number)\s*[:\-]\s*([\w\-/]+)",
    "issued_by":        r"Issued\s*By\s*[:\-]\s*(.+)",
    "issue_date":       r"Issue\s*Date\s*[:\-]\s*" + DATE,
    "valid_until":      r"Valid(?:ity)?\s*(?:Until|Till|Upto)\s*[:\-]\s*" + DATE,
    "academic_year":    [r"Academic\s*Year\s*[:\-]\s*([\d\-/]+)",
                         r"Academic\s*(?:Year|Session)" + SEP + r"(\d{4}\s*[-\u2013\u2014/]\s*\d{2,4})",
                         r"for\s*the\s*(?:Academic\s*)?(?:Year|Session)\s*(\d{4}\s*[-\u2013\u2014/]\s*\d{2,4})"],
    "programme":        r"Programme\s*[:\-]\s*(.+)",
    "approved_intake":  r"Approved\s*Intake\s*[:\-]?\s*(\d+)",
    "signatory":        r"Signatory\s*[:\-]\s*(.+)",
    "accreditation_body": r"Accreditation\s*Body\s*[:\-]\s*(.+)",
    "grade":            r"\bGrade\s*[:\-]?\s*([A-F][+]?)\b",
    "facility":         r"Facilit(?:y|ies)\s*[:\-]\s*(.+)",
    # --- AICTE Extension of Approval (EoA) letter ---
    "permanent_id":     r"Permanent\s*I\.?D\.?(?:\s*No\.?)?" + SEP + r"(\d+-\d+)",
    "application_id":   r"Application\s*(?:I\.?D\.?|No\.?|Number)" + SEP + r"(\d+-\d+)",
    "region":           r"\bRegion(?:al\s*Office)?" + SEP + r"([A-Za-z][A-Za-z \-]*[A-Za-z])",
    "institution_type": [r"Institution\s*Type" + SEP + r"([^\n]+)",
                         r"Type\s*of\s*(?:the\s*)?Institution" + SEP + r"([^\n]+)",
                         r"Institute\s*Type" + SEP + r"([^\n]+)"],
    "establishment_year": r"(?:Year\s*of\s*Establishment|Establishment\s*Year|Established\s*(?:in|on)?)" + SEP + r"((?:19|20)\d{2})",
    "approval_date":    [r"(?:Approval\s*Date|Date\s*of\s*(?:Approval|Issue))" + SEP + DATE_ANY,
                         r"(?<![A-Za-z] )\bDated?\s*[:\-]\s*" + DATE_ANY],  # bare "Date:" only, never "Issue Date:" etc.
}
OCR_LANGS = os.environ.get("OCR_LANGS", "eng")     # e.g. "eng+hin" once those tesseract packs are installed


# ------------------------------------------------------------------ image helpers
def preprocess(img):
    """Grayscale -> upscale small scans -> denoise -> adaptive threshold (OpenCV). Returns PIL image."""
    try:
        import cv2, numpy as np
        from PIL import Image
        a = np.array(img.convert("L"))
        if min(a.shape) < 1000:
            s = 1000 / min(a.shape)
            a = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        a = cv2.fastNlMeansDenoising(a, None, 10, 7, 21)
        a = cv2.adaptiveThreshold(a, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        return Image.fromarray(a), a.shape[1], a.shape[0]
    except Exception:
        return img.convert("L"), img.width, img.height


def _ocr_image(img):
    """Returns (text, words). words = (x0,y0,x1,y1,text,conf0to1) in ORIGINAL image pixel coords."""
    import pytesseract
    from pytesseract import Output
    proc, pw, ph = preprocess(img)
    sx, sy = img.width / pw, img.height / ph
    d = pytesseract.image_to_data(proc, lang=OCR_LANGS, output_type=Output.DICT)
    words, lines = [], {}
    for i, t in enumerate(d["text"]):
        t = t.strip()
        if not t:
            continue
        conf = float(d["conf"][i])
        if conf < 0:
            continue
        x0, y0 = d["left"][i] * sx, d["top"][i] * sy
        words.append((x0, y0, x0 + d["width"][i] * sx, y0 + d["height"][i] * sy, t, conf / 100.0))
        lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(t)
    return "\n".join(" ".join(v) for v in lines.values()), words


# ------------------------------------------------------------------ main extraction
def extract_pages(path):
    """Returns dict: pages=[{text, words}], method, mean_conf (0..1). Text layer first, OCR fallback."""
    ext = os.path.splitext(path)[1].lower()
    pages, method = [], "text_layer"
    if ext in IMAGE_EXT:
        try:
            from PIL import Image
            img = Image.open(path)
            text, words = _ocr_image(img)
            pages, method = [{"text": text, "words": words, "w": img.width, "h": img.height}], "ocr_tesseract"
        except Exception:
            return {"pages": [], "method": "unreadable", "mean_conf": 0.0}
    else:
        doc = fitz.open(path)
        for p in doc:
            words = [(w[0], w[1], w[2], w[3], w[4], 0.99) for w in p.get_text("words")]
            pages.append({"text": p.get_text(), "words": words, "w": p.rect.width, "h": p.rect.height})
        if not "".join(pg["text"] for pg in pages).strip():       # scanned PDF -> OCR
            try:
                from PIL import Image
                pages, method = [], "ocr_tesseract"
                for p in doc:
                    pix = p.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text, words = _ocr_image(img)
                    pages.append({"text": text, "words": words, "w": pix.width, "h": pix.height})
            except Exception:
                return {"pages": [], "method": "unreadable", "mean_conf": 0.0}
    confs = [w[5] for pg in pages for w in pg["words"]]
    mean = round(sum(confs) / len(confs), 3) if confs else 0.0
    if not "".join(pg["text"] for pg in pages).strip():
        method = "unreadable"
    return {"pages": pages, "method": method, "mean_conf": mean}


def classify(text, filename=""):
    """Keyword scoring with title boost. Returns (type, confidence). 'unknown' when nothing matches."""
    lines = [l for l in text.splitlines() if l.strip()]
    title = " ".join(lines[:2]).lower()
    t = text.lower()
    scores = {k: sum(t.count(w) + TITLE_BOOST * title.count(w) for w in ws) for k, ws in DOC_KEYWORDS.items()}
    fn = filename.lower()
    if "floor" in fn and "plan" in fn:
        scores["floor_plan"] += 5
    if re.search(r"photo|lab|classroom", fn):
        scores["infrastructure_photo"] += 5
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown", 0.0
    total = sum(scores.values())
    return best, round(scores[best] / total, 2)


def _locate(words, value):
    """Bounding box of the token run that spells `value` (merged). None when not found."""
    toks = value.split()
    if not toks:
        return None, 0.0
    for i in range(len(words)):
        if all(i + j < len(words) and words[i + j][4].strip(".,;:") == toks[j].strip(".,;:") for j in range(len(toks))):
            seg = words[i:i + len(toks)]
            return [round(min(w[0] for w in seg), 1), round(min(w[1] for w in seg), 1),
                    round(max(w[2] for w in seg), 1), round(max(w[3] for w in seg), 1)], \
                round(sum(w[5] for w in seg) / len(seg), 3)
    return None, 0.0


def _patterns(pat):
    return pat if isinstance(pat, (list, tuple)) else [pat]


def _norm_date(v):
    """03-Jan-2025 / 3 January 2025 / 03/01/2025 -> 03-01-2025 (the format the rules engine parses). None if unparseable."""
    from datetime import datetime
    t = re.sub(r"[\s/,]+", "-", v.strip()).strip("-")
    for f in ("%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(t, f).strftime("%d-%m-%Y")
        except ValueError:
            pass
    return None


def extract_fields(pages, method):
    """pages: list of {text, words}. Returns {field: {value, confidence, page, bbox}}"""
    fields = {}
    for pno, pg in enumerate(pages, start=1):
        for name, pat in FIELD_PATTERNS.items():
            if name in fields:
                continue
            val = None
            for p in _patterns(pat):
                m = re.search(p, pg["text"], re.I)
                if not m:
                    continue
                cand = re.sub(r"\s+", " ", m.group(1)).strip()
                if cand and not cand.endswith(":"):      # value was actually the next label -> try the next alternate
                    val = cand
                    break
            if not val:
                continue
            bbox, wconf = _locate(pg["words"], val)
            conf = wconf if bbox else (0.95 if method == "text_layer" else 0.6)   # located -> real word confidence
            if method == "text_layer":
                conf = max(conf, 0.95)
            fields[name] = {"value": val, "confidence": round(conf, 2), "page": pno, "bbox": bbox,
                            "pw": pg.get("w"), "ph": pg.get("h")}
    # An EoA carries no "Institution ID" / "Issue Date" labels: its Permanent ID identifies the institution and its
    # approval date is the date of issue, so the existing rules (mandatory fields, cross-document ID check) can run.
    if "institution_id" not in fields and "permanent_id" in fields:
        fields["institution_id"] = dict(fields["permanent_id"])
    if "issue_date" not in fields and "approval_date" in fields:
        iso = _norm_date(fields["approval_date"]["value"])
        if iso:
            fields["issue_date"] = {**fields["approval_date"], "value": iso}
    return fields


# ------------------------------------------------------------------ structured summary (shown after upload)
DOC_CATEGORY_LABEL = {
    "approval_record": "Extension of Approval (EoA)",
    "accreditation_certificate": "Accreditation certificate",
    "noc": "No Objection Certificate (NOC)",
    "affidavit": "Affidavit / undertaking",
    "infrastructure_certificate": "Infrastructure certificate",
    "floor_plan": "Floor plan",
    "infrastructure_photo": "Infrastructure photo",
}
def eoa_summary(doc_type, fields):
    """fields: {name: {value, confidence}}. Returns [(label, value|None, confidence|None)] for an EoA, else []."""
    from core.eoa import EOA_FIELDS
    if doc_type != "approval_record":
        return []
    rows = [("Document category", DOC_CATEGORY_LABEL[doc_type], None)]
    for label, key in EOA_FIELDS:
        f = fields.get(key)
        rows.append((label, f["value"] if f else None, f.get("confidence") if f else None))
    return rows


def eoa_review(doc_type, fields, findings=()):
    """What the officer sees for an EoA: every particular listed with its own status, plus the document's problems.
    fields: {name: {value, confidence}}; findings: FAIL/INCONCLUSIVE rule results whose source is this document.
    Returns None when the document is not an EoA, else {headline, level, rows:[{label,value,conf,status,level,note}], alerts:[...]}"""
    from core.eoa import EOA_FIELDS, looks_like_eoa
    if doc_type != "approval_record" or not (looks_like_eoa(fields) or "certificate_no" not in fields):   # old-format records carry a certificate no.; an unreadable EoA still gets its table (all Missing)
        return None
    expired = [f for f in findings if str(f.get("reason", "")).startswith("Expired")]
    rows = [{"label": "Document category", "value": DOC_CATEGORY_LABEL[doc_type], "conf": None, "status": "Identified", "level": "ok", "note": ""}]
    missing = []
    for label, key in EOA_FIELDS:
        f = fields.get(key)
        if not f or not str(f.get("value", "")).strip():
            rows.append({"label": label, "value": None, "conf": None, "status": "Missing", "level": "bad", "note": "Not found - check the original"})
            missing.append(label)
            continue
        conf = f.get("confidence")
        row = {"label": label, "value": f["value"], "conf": conf, "status": "Found", "level": "ok", "note": ""}
        if conf is not None and conf < 0.8:
            row.update(status="Check", level="warn", note="Low OCR confidence - compare with the original")
        if key == "academic_year" and expired:
            row.update(status="Expired", level="bad", note=expired[0]["reason"])
        rows.append(row)
    alerts = [{"level": "bad" if f.get("status") == "FAIL" else "warn", "text": f"{f.get('title')}: {f.get('reason') or f.get('observed')}"} for f in findings]
    if expired:
        headline, level = "Expired", "bad"
    elif missing:
        headline, level = f"Incomplete - {len(missing)} field(s) missing", "bad"
    elif alerts:
        headline, level = "Needs officer attention", "warn"
    else:
        headline, level = "All particulars found", "ok"
    return {"headline": headline, "level": level, "rows": rows, "alerts": alerts, "missing": missing}


_PAIR = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 .&/()'\-]{1,45}?)\s*[:\u2013\-]\s*(\S.*)$")


def text_pairs(text, limit=80):
    """Every 'Label : value' line found in the document text - lets an officer see what was read even where no field pattern matched."""
    out = []
    for line in text.splitlines():
        m = _PAIR.match(line)
        if m and len(m.group(2)) < 200:
            out.append((m.group(1).strip(), m.group(2).strip()))
        if len(out) >= limit:
            break
    return out
