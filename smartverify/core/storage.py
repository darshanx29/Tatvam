"""Encrypted-at-rest document storage (Fernet). Swap this class for S3/MinIO later: same interface."""
import os, shutil, tempfile
from cryptography.fernet import Fernet, InvalidToken
from core.security import secure_delete

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _key():
    k = os.environ.get("DOC_ENCRYPTION_KEY")
    if k:
        return k.encode()
    path = os.path.join(BASE, "instance", "doc.key")        # dev fallback only; use a secret manager in production
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(Fernet.generate_key())
        try: os.chmod(path, 0o600)
        except OSError: pass
    return open(path, "rb").read().strip()


class EncryptedLocalStorage:
    def __init__(self, root):
        self.root, self.f = root, Fernet(_key())

    def _p(self, app_id, name):
        return os.path.join(self.root, app_id, name + ".enc")

    def save(self, app_id, name, data: bytes):
        os.makedirs(os.path.join(self.root, app_id), exist_ok=True)
        with open(self._p(app_id, name), "wb") as fh:
            fh.write(self.f.encrypt(data))

    def read(self, app_id, name) -> bytes:
        try:
            return self.f.decrypt(open(self._p(app_id, name), "rb").read())
        except (InvalidToken, FileNotFoundError):
            raise FileNotFoundError(name)

    def exists(self, app_id, name):
        return os.path.exists(self._p(app_id, name))

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
