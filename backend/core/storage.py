"""Encrypted-at-rest document storage (Fernet). Swap this class for S3/MinIO later: same interface."""
import os, re, shutil, tempfile
from cryptography.fernet import Fernet, InvalidToken
from core.security import secure_delete

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _key():
    k = os.environ.get("DOC_ENCRYPTION_KEY")
    if k:
        return k.encode()
    # Check root instance/doc.key first, then backend/instance/doc.key
    root_instance = os.path.abspath(os.path.join(BASE, "..", "instance", "doc.key"))
    backend_instance = os.path.join(BASE, "instance", "doc.key")
    path = root_instance if os.path.exists(root_instance) else backend_instance
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(Fernet.generate_key())
        try: os.chmod(path, 0o600)
        except OSError: pass
    return open(path, "rb").read().strip()


class EncryptedLocalStorage:
    def __init__(self, root):
        self.root, self.f = os.path.abspath(root), Fernet(_key())

    def _p(self, app_id, name):
        safe_app = re.sub(r"[^A-Za-z0-9_-]", "", str(app_id))
        safe_name = os.path.basename(str(name))
        target = os.path.abspath(os.path.join(self.root, safe_app, safe_name + ".enc"))
        if not target.startswith(self.root):
            raise ValueError("Path traversal attempt detected")
        return target

    def save(self, app_id, name, data: bytes):
        os.makedirs(os.path.join(self.root, app_id), exist_ok=True)
        with open(self._p(app_id, name), "wb") as fh:
            fh.write(self.f.encrypt(data))

    def read(self, app_id, name) -> bytes:
        p = self._p(app_id, name)
        if not os.path.exists(p):
            # Check alternate uploads location (root uploads vs backend/uploads)
            alt_root = os.path.abspath(os.path.join(self.root, "..", "uploads")) if "backend" in self.root else os.path.abspath(os.path.join(self.root, "backend", "uploads"))
            alt_p = os.path.join(alt_root, re.sub(r"[^A-Za-z0-9_-]", "", str(app_id)), os.path.basename(str(name)) + ".enc")
            if os.path.exists(alt_p):
                p = alt_p
        try:
            with open(p, "rb") as fh:
                return self.f.decrypt(fh.read())
        except (InvalidToken, FileNotFoundError):
            raise FileNotFoundError(name)

    def exists(self, app_id, name):
        if os.path.exists(self._p(app_id, name)):
            return True
        alt_root = os.path.abspath(os.path.join(self.root, "..", "uploads")) if "backend" in self.root else os.path.abspath(os.path.join(self.root, "backend", "uploads"))
        alt_p = os.path.join(alt_root, re.sub(r"[^A-Za-z0-9_-]", "", str(app_id)), os.path.basename(str(name)) + ".enc")
        return os.path.exists(alt_p)

    def names(self, app_id):
        d = os.path.join(self.root, app_id)
        return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".enc")) if os.path.isdir(d) else []

    def materialize(self, app_id):
        """Decrypts the application's files into a private temp dir for OCR. Caller must call cleanup()."""
        tmp = tempfile.mkdtemp(prefix="sv_")
        for n in self.names(app_id):
            with open(os.path.join(tmp, n), "wb") as fh:
                fh.write(self.read(app_id, n))
        return tmp

    @staticmethod
    def cleanup(tmp):
        for fn in os.listdir(tmp):
            secure_delete(os.path.join(tmp, fn))
        shutil.rmtree(tmp, ignore_errors=True)

    def delete(self, app_id, name):
        p = self._p(app_id, name)
        if os.path.exists(p): secure_delete(p)

    def delete_app(self, app_id):
        for n in self.names(app_id): self.delete(app_id, n)
