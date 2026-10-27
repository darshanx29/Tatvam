"""Preliminary anomaly indicators. These are REVIEW FLAGS, never proof of forgery.
Scanning, recompression or conversion can legitimately change metadata and image statistics."""
import hashlib, io, os, re, difflib
from datetime import datetime
import numpy as np
import pymupdf as fitz
from PIL import Image

EDITOR_HINTS = re.compile(r"photoshop|canva|ilovepdf|smallpdf|sejda|foxit phantom|gimp|pixlr", re.I)
IMAGE_EXT = (".jpg", ".jpeg", ".png")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- perceptual hash (numpy only, 64-bit)
def _dct_matrix(n):
    k = np.arange(n)[:, None]; i = np.arange(n)[None, :]
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2 / n)
    m[0] /= np.sqrt(2)
    return m


_D = _dct_matrix(32)


def _phash_img(img):
    a = np.asarray(img.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
    low = (_D @ a @ _D.T)[:8, :8]
    return (low > np.median(low[1:].ravel() if low.size > 1 else low)).ravel()


def page_hashes(path):
    """One 64-bit perceptual hash (bool array) per page (max 5 pages) - not just page 1."""
    if path.lower().endswith(IMAGE_EXT):
        return [_phash_img(Image.open(path))]
    out = []
    for i, p in enumerate(fitz.open(path)):
        if i >= 5:
            break
        pix = p.get_pixmap(dpi=50)
        out.append(_phash_img(Image.frombytes("RGB", [pix.width, pix.height], pix.samples)))
    return out


def hamming(h1, h2):
    """Distance between two documents' page-hash lists (mean over compared pages)."""
    n = min(len(h1), len(h2))
    if n == 0 or len(h1) != len(h2):
        return 64
    return sum(int(np.count_nonzero(h1[i] != h2[i])) for i in range(n)) / n


# ---------------------------------------------------------------- metadata & structure
def _pdf_date(s):
    m = re.match(r"D:(\d{14})", s or "")
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S") if m else None


def metadata_flags(path):
    if not path.lower().endswith(".pdf"):
        return []
    md = fitz.open(path).metadata or {}
    flags = []
    prod = f"{md.get('producer', '')} {md.get('creator', '')}"
    if EDITOR_HINTS.search(prod):
        flags.append(f"Producer/creator suggests an editing tool: '{prod.strip()}'")
    c, m = _pdf_date(md.get("creationDate")), _pdf_date(md.get("modDate"))
    if c and m and (m - c).days >= 1:
        flags.append(f"Modified {(m - c).days} day(s) after creation ({c:%d-%m-%Y} -> {m:%d-%m-%Y})")
    elif c and m and (m < c):
        flags.append(f"Temporal inconsistency: modification date precedes creation date ({m:%d-%m-%Y} < {c:%d-%m-%Y})")
    return flags


def structure_flags(path):
    """Raw-byte inspection of PDF structure: incremental updates, active content, embedded files, signatures."""
    if not path.lower().endswith(".pdf"):
        return []
    with open(path, "rb") as fh:
        raw = fh.read()
    flags = []
    if raw.count(b"%%EOF") > 1 and b"/Linearized" not in raw[:2048]:
        flags.append(f"PDF has {raw.count(b'%%EOF')} end-of-file markers (saved incrementally after creation)")
    for tag, label in ((b"/JavaScript", "JavaScript"), (b"/Launch", "launch action"),
                       (b"/EmbeddedFile", "embedded file"), (b"/OpenAction", "open-action")):
        if tag in raw:
            flags.append(f"PDF contains {label} content")
    return flags


def signature_status(path):
    """Returns (state, detail): 'none' | 'present_unvalidated' | 'valid' | 'invalid'.
    Performs cryptographic validation through pyHanko and PKCS#7 X.509 certificate parsing."""
    if not path.lower().endswith(".pdf"):
        return "none", ""
    with open(path, "rb") as fh:
        raw = fh.read()
    if b"/ByteRange" not in raw or b"/Sig" not in raw:
        return "none", ""
    try:
        from core import ml_service
        res = ml_service.verify_pdf_signatures(path)
        if not res["has_signature"]:
            return "none", ""
        st = res["status"]
        if st == "cryptographically_valid":
            return "valid", res["detail"]
        elif st in ("invalid", "expired", "integrity_compromised"):
            return "invalid", res["detail"]
        else:
            return "present_unvalidated", res["detail"]
    except Exception:
        pass
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
        r = PdfFileReader(open(path, "rb"))
        bad = [s.field_name for s in r.embedded_signatures if not validate_pdf_signature(s).bottom_line]
        return ("invalid", f"Signature validation failed: {bad}") if bad else ("valid", "Embedded signature validated")
    except ImportError:
        return "present_unvalidated", "Digital signature present; install pyHanko and trusted roots to validate it"
    except Exception as e:
        return "invalid", f"Signature could not be validated ({type(e).__name__})"


# ---------------------------------------------------------------- QR
def qr_payloads(path):
    """Decode QR codes (OpenCV) on the first 3 pages / the image. Returns list of strings."""
    import cv2
    imgs = []
    if path.lower().endswith(IMAGE_EXT):
        imgs = [Image.open(path).convert("RGB")]
    else:
        for i, p in enumerate(fitz.open(path)):
            if i >= 3: break
            pix = p.get_pixmap(dpi=150)
            imgs.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    out = []
    det = cv2.QRCodeDetector()
    for im in imgs:
        try:
            val, _, _ = det.detectAndDecode(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
            if val: out.append(val)
        except Exception:
            pass
    return out


# ---------------------------------------------------------------- image tampering indicator (ELA) - EXPERIMENTAL
def ela_flag(path, quality=90, block=32, z_thresh=8.0):
    """EXPERIMENTAL, OFF by default (set ENABLE_ELA=1). Content-normalised error-level analysis for JPEGs.
    It could NOT reliably separate edited from clean test images on our synthetic data, so it must not be
    relied on until it is validated on a labelled real-world set (see evaluate.py). Preliminary flag only."""
    import os
    if os.environ.get("ENABLE_ELA") != "1" or not path.lower().endswith((".jpg", ".jpeg")):
        return None
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality)
    re_im = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    diff = np.abs(np.asarray(im, dtype=float) - np.asarray(re_im, dtype=float)).mean(axis=2)
    gy, gx = np.gradient(np.asarray(im.convert("L"), dtype=float)); grad = np.hypot(gx, gy)
    h, w = diff.shape; bh, bw = h // block, w // block
    if bh < 4 or bw < 4:
        return None
    E = diff[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3))
    G = grad[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3))
    m = G > 1.0
    if m.sum() < 8:
        return None
    r = np.zeros_like(E); r[m] = E[m] / (G[m] + 1.0)
    vals = r[m]; med = np.median(vals); mad = np.median(np.abs(vals - med)) + 1e-6
    z = np.zeros_like(r); z[m] = (r[m] - med) / (1.4826 * mad)
    hot = np.argwhere(z > z_thresh)
    if len(hot) == 0:
        return None
    y0, x0 = hot.min(axis=0) * block; y1, x1 = (hot.max(axis=0) + 1) * block
    return {"reason": f"Localised compression inconsistency ({len(hot)} block(s)) - possible edited region (experimental check)",
            "bbox": [int(x0), int(y0), int(x1), int(y1)]}


# ---------------------------------------------------------------- duplicates
def duplicate_flags(docs):
    """docs: dicts with name, sha, phashes, text. Returns (a, b, reason) tuples (within one application)."""
    out = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            if a["sha"] == b["sha"]:
                out.append((a["name"], b["name"], "Identical file (same SHA-256)"))
            else:
                sim = difflib.SequenceMatcher(None, a["text"], b["text"]).ratio()
                if hamming(a["phashes"], b["phashes"]) <= 4 and sim >= 0.9:
                    out.append((a["name"], b["name"], f"Near-identical (text similarity {sim:.2f})"))
    return out


# ---------------------------------------------------------------- hash (de)serialisation for cross-application search
def hashes_to_str(hs):
    return ",".join(np.packbits(h).tobytes().hex() for h in hs)


def hashes_from_str(s):
    return [np.unpackbits(np.frombuffer(bytes.fromhex(x), dtype=np.uint8)).astype(bool) for x in (s or "").split(",") if x]
