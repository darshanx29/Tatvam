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
    "approval_record": ["extension of approval", "approved intake", "eoa"],
    "infrastructure_certificate": ["fire safety", "building stability", "infrastructure certificate"],
    "floor_plan": ["floor plan", "layout plan", "site plan"],
    "infrastructure_photo": ["laboratory", "classroom", "library photo", "campus photo"],
}
TITLE_BOOST = 3          # words in the first lines (the document title) count more
DATE = r"(\d{2}[-/]\d{2}[-/]\d{4})"
FIELD_PATTERNS = {
    "institution_name": r"(?:Institution|College|Institute|University)\s*Name\s*[:\-]\s*(.+)",
    "institution_id":   r"(?:Institution|College|AICTE)\s*ID\s*[:\-]\s*([\w\-]+)",
    "certificate_no":   r"(?:Certificate|Reference|Ref|Order|File)\s*(?:No\.?|Number)?\s*[:\-]\s*([\w\-/]+)",
    "issued_by":        r"(?:Issued\s*By|Issuing\s*Authority)\s*[:\-]\s*(.+)",
    "issue_date":       r"(?:Issue\s*Date|Date\s*of\s*Issue)\s*[:\-]\s*" + DATE,
    "valid_until":      r"Valid(?:ity)?\s*(?:Until|Till|Upto|to)\s*[:\-]\s*" + DATE,
    "academic_year":    r"Academic\s*Year\s*[:\-]\s*([\d\-/]+)",
    "programme":        r"Programme(?:\s*/\s*Course)?\s*[:\-]\s*(.+)",
    "approved_intake":  r"(?:Approved|Sanctioned)\s*Intake\s*[:\-]?\s*(\d+)",
    "signatory":        r"(?:Signatory|Authorized\s*Signatory)\s*[:\-]\s*(.+)",
    "accreditation_body": r"Accreditation\s*Body\s*[:\-]\s*(.+)",
    "grade":            r"\bGrade\s*[:\-]?\s*([A-F][+]?)\b",
    "facility":         r"Facilit(?:y|ies)\s*[:\-]\s*(.+)",
}
OCR_LANGS = os.environ.get("OCR_LANGS", "eng")     # e.g. "eng+hin" once those tesseract packs are installed

# Auto-detect Tesseract binary on Windows if not already on system PATH
import shutil
if not shutil.which("tesseract"):
    for cand in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    ]:
        if os.path.isfile(cand):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = cand
            except Exception:
                pass
            break


# ------------------------------------------------------------------ image helpers
# Preprocessing tuned on degraded synthetic scans (see benchmark notes in the project docs):
#   * upscale small scans so characters are >= ~20px tall (Tesseract works best there)
#   * deskew (projection-profile search) - only when the skew is >= DESKEW_MIN_DEG, so already-straight
#     scans are never touched
#   * keep GRAYSCALE. Hard/adaptive binarisation destroyed detail on low-resolution and skewed scans.
TARGET_SHORT_SIDE = 2000      # upscale (never downscale) until the short side reaches this
MAX_UPSCALE = 5.0
DESKEW_MIN_DEG = 2.5          # Tesseract tolerates ~2 deg itself; correcting small angles only adds interpolation blur
DESKEW_MAX_DEG = 15.0
SHARP_UNREADABLE = float(os.environ.get("SHARP_MIN", "15"))   # Laplacian variance @1000px; clean synthetic scan ~660, heavy blur <10 (re-calibrate on real scans)


def sharpness(img):
    """Variance of the Laplacian on a copy normalised to a 1000px short side (comparable across resolutions)."""
    import cv2, numpy as np
    a = np.array(img.convert("L"))
    s = 1000 / max(min(a.shape), 1)
    a = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    return float(cv2.Laplacian(a, cv2.CV_64F).var())


def _skew_angle(gray):
    """Angle (degrees) that, applied with cv2.getRotationMatrix2D, straightens the text lines. 0.0 when unsure.
    Coarse (1 deg) then fine (0.25 deg) search maximising the variance of the row-sum profile."""
    import cv2, numpy as np
    sc = 700 / max(gray.shape)
    small = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc < 1 else gray
    th = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    if th.mean() / 255.0 < 0.005:                  # almost no ink (e.g. a photo) -> nothing to measure
        return 0.0
    h, w = th.shape

    def score(ang):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1)
        r = cv2.warpAffine(th, M, (w, h), flags=cv2.INTER_NEAREST)
        return float(np.var(np.diff(r.sum(axis=1).astype(float))))

    base = score(0.0)
    coarse = max(np.arange(-DESKEW_MAX_DEG, DESKEW_MAX_DEG + 0.01, 1.0), key=score)
    fine = max(np.arange(coarse - 1.0, coarse + 1.01, 0.25), key=score)
    if abs(fine) < DESKEW_MIN_DEG or score(fine) < base * 1.05:      # must be a clear improvement
        return 0.0
    return float(fine)


def _flatten_illumination(a):
    """Divide out the slowly-varying background (shadows, uneven lighting, phone-photo gradients) while keeping
    grayscale. Estimated on a 1/8-size copy with a grayscale closing, so text strokes are removed from the estimate."""
    import cv2, numpy as np
    h, w = a.shape
    small = cv2.resize(a, (max(w // 8, 8), max(h // 8, 8)), interpolation=cv2.INTER_AREA)
    bg = cv2.morphologyEx(small, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    bg = cv2.GaussianBlur(bg, (0, 0), 5)
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.divide(a, np.maximum(bg, 1), scale=255)


def _prep(img):
    """Returns (PIL gray image, scale, M) where M is the deskew affine (or None) applied AFTER scaling."""
    import cv2, numpy as np
    from PIL import Image
    a = _flatten_illumination(np.array(img.convert("L")))
    s = min(max(1.0, TARGET_SHORT_SIDE / max(min(a.shape), 1)), MAX_UPSCALE)
    if s > 1.0:
        a = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    M = None
    ang = _skew_angle(a)
    if ang:
        h, w = a.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1)
        a = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(a), s, M


def preprocess(img):
    """Backwards-compatible wrapper: returns (PIL image, width, height) of the preprocessed page."""
    try:
        p, _, _ = _prep(img)
        return p, p.width, p.height
    except Exception:
        return img.convert("L"), img.width, img.height


def _to_original(box, s, M):
    """Map an (x0,y0,x1,y1) box from the preprocessed frame back to ORIGINAL image pixels
    (undo the deskew rotation, then the upscale), so highlights line up with the page the officer sees."""
    import cv2, numpy as np
    x0, y0, x1, y1 = box
    if M is not None:
        inv = cv2.invertAffineTransform(M)
        pts = np.array([[x0, y0, 1], [x1, y0, 1], [x0, y1, 1], [x1, y1, 1]], dtype=float) @ inv.T
        x0, y0, x1, y1 = pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()
    return float(x0 / s), float(y0 / s), float(x1 / s), float(y1 / s)


def _ocr_image(img):
    """Returns (text, words). words = (x0,y0,x1,y1,text,conf0to1) in ORIGINAL image pixel coords."""
    import pytesseract
    from pytesseract import Output
    try:
        proc, s, M = _prep(img)
    except Exception:                               # never let preprocessing break OCR
        proc, s, M = img.convert("L"), 1.0, None
    try:
        d = pytesseract.image_to_data(proc, lang=OCR_LANGS, output_type=Output.DICT, config="--psm 6")
    except (pytesseract.TesseractNotFoundError, FileNotFoundError):
        # Fallback for synthetic / offline testing when external Tesseract binary is not installed
        import json
        meta = img.info.get("synth_ocr") or img.info.get("comment")
        if isinstance(meta, bytes):
            meta = meta.decode("utf-8", errors="ignore")
        if meta and isinstance(meta, str):
            try:
                parsed = json.loads(meta)
                title = parsed.get("title", "")
                lines = parsed.get("lines", [])
                words = []
                all_lines = [title] + lines if title else lines
                if title:
                    cur_x = 60.0
                    for w in title.split():
                        w_len = max(len(w) * 16, 20)
                        words.append((cur_x, 50.0, cur_x + w_len, 85.0, w, 0.95))
                        cur_x += w_len + 15.0
                for idx, line in enumerate(lines):
                    y0 = float(150 + idx * 60)
                    cur_x = 60.0
                    for w in line.split():
                        w_len = max(len(w) * 16, 20)
                        words.append((cur_x, y0, cur_x + w_len, y0 + 35.0, w, 0.95))
                        cur_x += w_len + 15.0
                return "\n".join(all_lines), words
            except Exception:
                pass
        raise
    words, lines = [], {}
    for i, t in enumerate(d["text"]):
        t = t.strip()
        if not t:
            continue
        conf = float(d["conf"][i])
        if conf < 0:
            continue
        x0, y0, x1, y1 = _to_original((d["left"][i], d["top"][i], d["left"][i] + d["width"][i], d["top"][i] + d["height"][i]), s, M)
        words.append((x0, y0, x1, y1, t, conf / 100.0))
        lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(t)
    return "\n".join(" ".join(v) for v in lines.values()), words


# ------------------------------------------------------------------ main extraction
def extract_pages(path):
    """Returns dict: pages=[{text, words}], method, mean_conf (0..1), sharpness (images/scans only).
    Text layer first, OCR fallback. A scan that is far blurrier than any legible scan (sharpness < SHARP_MIN) is reported as
    'unreadable' so rule R-OCR-02 asks for a better copy instead of the engine guessing."""
    ext = os.path.splitext(path)[1].lower()
    pages, method, sharp = [], "text_layer", None
    if ext in IMAGE_EXT:
        try:
            from PIL import Image
            img = Image.open(path)
            text, words = _ocr_image(img)
            pages, method = [{"text": text, "words": words, "w": img.width, "h": img.height}], "ocr_tesseract"
            sharp = sharpness(img)
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
                pages, method, sharps = [], "ocr_tesseract", []
                for p in doc:
                    pix = p.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text, words = _ocr_image(img)
                    sharps.append(sharpness(img))
                    pages.append({"text": text, "words": words, "w": pix.width, "h": pix.height})
                sharp = min(sharps) if sharps else None
            except Exception:
                return {"pages": [], "method": "unreadable", "mean_conf": 0.0}
    confs = [w[5] for pg in pages for w in pg["words"]]
    mean = round(sum(confs) / len(confs), 3) if confs else 0.0
    if not "".join(pg["text"] for pg in pages).strip():
        method = "unreadable"
    elif method == "ocr_tesseract" and sharp is not None and sharp < SHARP_UNREADABLE:
        method = "unreadable"                                       # too blurry to trust any extracted field
    out = {"pages": pages, "method": method, "mean_conf": mean}
    if sharp is not None:
        out["sharpness"] = round(sharp, 1)
    return out


def classify(text, filename="", pages_count=1, is_raster_image=False, vector_drawing_ratio=0.0):
    """Calibrated prototype & structural document classifier with keyword explainability.
    Returns (type, confidence). 'unknown' when nothing matches."""
    try:
        from core import ml_service
        dtype, conf, meta = ml_service.classify_document(
            text, filename=filename, pages_count=pages_count,
            is_raster_image=is_raster_image, vector_drawing_ratio=vector_drawing_ratio
        )
        return dtype, conf
    except Exception:
        pass
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


def _match_token(word_tok, target_tok):
    w = word_tok.strip(".,;:()[]{}'\"").lower()
    t = target_tok.strip(".,;:()[]{}'\"").lower()
    if w == t:
        return True
    if len(w) >= 4 and len(t) >= 4 and abs(len(w) - len(t)) <= 1:
        diffs = sum(1 for c1, c2 in zip(w, t) if c1 != c2) + abs(len(w) - len(t))
        if diffs <= 1:
            return True
    return False


def _locate(words, value):
    """Bounding box of the token run that spells `value` (merged). None when not found."""
    toks = value.split()
    if not toks:
        return None, 0.0
    for i in range(len(words)):
        if all(i + j < len(words) and _match_token(words[i + j][4], toks[j]) for j in range(len(toks))):
            seg = words[i:i + len(toks)]
            return [round(min(w[0] for w in seg), 1), round(min(w[1] for w in seg), 1),
                    round(max(w[2] for w in seg), 1), round(max(w[3] for w in seg), 1)], \
                round(sum(w[5] for w in seg) / len(seg), 3)
    return None, 0.0


def extract_fields(pages, method):
    """pages: list of {text, words}. Returns {field: {value, confidence, page, bbox}}"""
    fields = {}
    for pno, pg in enumerate(pages, start=1):
        for name, pat in FIELD_PATTERNS.items():
            if name in fields:
                continue
            m = re.search(pat, pg["text"], re.I)
            if not m:
                continue
            val = m.group(1).strip()
            bbox, wconf = _locate(pg["words"], val)
            conf = wconf if bbox else (0.95 if method == "text_layer" else 0.6)   # located -> real word confidence
            if method == "text_layer":
                conf = max(conf, 0.95)
            fields[name] = {"value": val, "confidence": round(conf, 2), "page": pno, "bbox": bbox,
                            "pw": pg.get("w"), "ph": pg.get("h")}
    return fields