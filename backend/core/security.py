"""Upload validation, malware screening, CSRF helpers, password policy and SSRF guard."""
import hashlib, hmac, ipaddress, os, re, secrets, shutil, socket, subprocess, tempfile
from io import BytesIO
from urllib.parse import urlparse

MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_MB", "10")) * 1024 * 1024
MAX_FILES_PER_UPLOAD = 20
MAX_PDF_PAGES = 50
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED = {".pdf": "pdf", ".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png"}
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def sniff(data: bytes):
    if data.startswith(b"%PDF-"): return "pdf"
    if data.startswith(b"\xff\xd8\xff"): return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    return None


def clamav_scan(data: bytes):
    """Uses clamscan if installed (returns reason string when infected). Optional hardening."""
    exe = shutil.which("clamscan")
    if not exe:
        return None
    with tempfile.NamedTemporaryFile(delete=False) as t:
        t.write(data); p = t.name
    try:
        r = subprocess.run([exe, "--no-summary", p], capture_output=True, timeout=60)
        return "Malware signature detected by ClamAV" if r.returncode == 1 else None
    except Exception:
        return None
    finally:
        os.unlink(p)


def validate_upload(filename: str, data: bytes):
    """Returns (ok, kind_or_reason). Checks size, extension, magic bytes, structure and malware."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED:
        return False, "Unsupported file type (PDF, JPEG, PNG only)"
    if not data:
        return False, "Empty file"
    if len(data) > MAX_FILE_BYTES:
        return False, f"File larger than {MAX_FILE_BYTES // (1024 * 1024)} MB"
    kind = sniff(data)
    if kind != ALLOWED[ext]:
        return False, "File content does not match its extension"
    if EICAR in data:
        return False, "Malware test signature detected"
    hit = clamav_scan(data)
    if hit:
        return False, hit
    if kind == "pdf":
        pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
        if pages > MAX_PDF_PAGES:
            return False, f"PDF has more than {MAX_PDF_PAGES} pages"
        if b"/Encrypt" in data:
            return False, "Encrypted PDFs cannot be processed"
    else:
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            im = Image.open(BytesIO(data)); im.verify()
            if im.width * im.height > MAX_IMAGE_PIXELS:
                return False, "Image dimensions too large"
        except Exception:
            return False, "Image is corrupt or unreadable"
    return True, kind


# ---------------- CSRF
def new_csrf():
    return secrets.token_urlsafe(32)


def csrf_ok(session_token, supplied):
    return bool(session_token and supplied) and hmac.compare_digest(session_token, supplied)


# ---------------- passwords
def password_problem(pw: str):
    if len(pw) < 10: return "Password must be at least 10 characters"
    if not re.search(r"[a-z]", pw) or not re.search(r"[A-Z]", pw): return "Use upper and lower case letters"
    if not re.search(r"\d", pw): return "Include at least one digit"
    return None


# ---------------- SSRF guard (used before ANY outbound fetch of a QR / URL target)
def validate_outbound_url(url: str, allowed_hosts):
    """Only https, only allow-listed hosts, never private/loopback/link-local addresses.
    Returns (ok, reason). The prototype never fetches; adapters must call this first."""
    try:
        u = urlparse(url)
    except Exception:
        return False, "Malformed URL"
    if u.scheme != "https":
        return False, "Only https URLs are permitted"
    host = (u.hostname or "").lower()
    if not host:
        return False, "No host"
    if u.username or u.password:
        return False, "Credentials in URL are not permitted"
    allowed = [h.lower() for h in allowed_hosts]
    if not any(host == h or host.endswith("." + h) for h in allowed):
        return False, "Host is not on the authorized verification allow-list"
    try:
        for fam, _, _, _, sa in socket.getaddrinfo(host, u.port or 443):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False, "Host resolves to a non-public address"
    except socket.gaierror:
        pass   # unresolved here is not an SSRF risk; the fetch itself would fail
    return True, "ok"


def host_allowed(url: str, allowed_hosts):
    """Pure string check (no DNS) used for QR classification."""
    try:
        u = urlparse(url)
    except Exception:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h.lower() or host.endswith("." + h.lower()) for h in allowed_hosts)


def secure_delete(path):
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            f.write(os.urandom(size)); f.flush(); os.fsync(f.fileno())
    except OSError:
        pass
    try:
        os.unlink(path)
    except OSError:
        pass
