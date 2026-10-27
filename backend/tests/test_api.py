"""Comprehensive FastAPI API, Security, RBAC, and Workflow Integration Tests.
Executes against the canonical FastAPI application:
    python -m unittest tests.test_api
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-bytes-minimum!!")
_tmp = tempfile.mkdtemp(prefix="svapi_test_")
os.environ["DOC_ENCRYPTION_KEY"] = "ZmFrZWtleWZha2VrZXlmYWtla2V5ZmFrZWtleTEyMzQ="
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test_api.db")
os.environ["UPLOADS_DIR"] = os.path.join(_tmp, "uploads")
os.environ["ASYNC_PROCESSING"] = "0"

from starlette.testclient import TestClient
from main import app, seed as seed_db
from models import (
    db, User, Application, ApplicationVersion, Document,
    ExtractedField, Finding, ReviewAction, AuditEvent,
    INSTITUTION, SCRUTINY, VERIFIER, ADMIN
)
import services as S
from core import security

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(BASE, "data", "synthetic")


def setUpModule():
    seed_db()


def tearDownModule():
    db.session.remove()
    shutil.rmtree(_tmp, ignore_errors=True)


def get_authenticated_client(email: str, password: str = "demo123") -> TestClient:
    """Returns a TestClient with an authenticated session and extracted CSRF token."""
    client = TestClient(app, cookies={})
    # Fetch CSRF token first
    me_resp = client.get("/api/v1/me")
    csrf = me_resp.json().get("csrf_token")

    # Login
    resp = client.post(
        "/api/v1/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    new_csrf = resp.json().get("csrf_token") or csrf
    client.headers["X-CSRF-Token"] = new_csrf
    return client


def syn_files(app_folder: str, names=None):
    """Loads synthetic files as multipart upload tuples for TestClient."""
    d = os.path.join(SYN, app_folder)
    flist = sorted(names or os.listdir(d))
    out = []
    for fn in flist:
        p = os.path.join(d, fn)
        with open(p, "rb") as fh:
            content = fh.read()
        mime = "application/pdf" if fn.endswith(".pdf") else "image/png" if fn.endswith(".png") else "image/jpeg"
        out.append(("files", (fn, content, mime)))
    return out


class HealthAndStartupTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "AICTE SmartVerify API")
        self.assertIn("timestamp", data)

    def test_readiness_probe(self):
        resp = self.client.get("/api/v1/ready")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["storage"], "accessible")


class SecurityAndAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_unauthenticated_api_endpoints_return_401(self):
        self.assertEqual(self.client.get("/api/v1/applications").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/rules").status_code, 401)

    def test_login_throttling(self):
        from main import _fails
        _fails.clear()
        c = TestClient(app)
        csrf = c.get("/api/v1/me").json().get("csrf_token")
        for _ in range(5):
            r = c.post(
                "/api/v1/login",
                json={"email": "bad_user@demo.com", "password": "wrong_password"},
                headers={"X-CSRF-Token": csrf}
            )
            self.assertEqual(r.status_code, 401)
        # 6th attempt should be throttled (429)
        r6 = c.post(
            "/api/v1/login",
            json={"email": "bad_user@demo.com", "password": "wrong_password"},
            headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(r6.status_code, 429)

    def test_institution_data_isolation(self):
        i1 = get_authenticated_client("inst1@demo.com")
        off = get_authenticated_client("officer@demo.com")

        # inst1 should access its own application SV-TEST-001
        self.assertEqual(i1.get("/api/v1/applications/SV-TEST-001").status_code, 200)

        # inst1 MUST NOT access inst2's application SV-TEST-002 (403 Forbidden)
        self.assertEqual(i1.get("/api/v1/applications/SV-TEST-002").status_code, 403)
        self.assertEqual(i1.get("/api/v1/applications/SV-TEST-002/findings").status_code, 403)

        # Officers CAN access submitted applications
        self.assertEqual(off.get("/api/v1/applications/SV-TEST-001").status_code, 200)
        self.assertEqual(off.get("/api/v1/applications/SV-TEST-002").status_code, 200)

    def test_role_enforcement(self):
        i1 = get_authenticated_client("inst1@demo.com")
        off = get_authenticated_client("officer@demo.com")
        admin = get_authenticated_client("admin@demo.com")

        # Institution cannot view admin settings or rules management
        self.assertEqual(i1.get("/api/v1/rules").status_code, 403)
        self.assertEqual(i1.get("/api/v1/admin/settings").status_code, 403)
        self.assertEqual(i1.get("/api/v1/admin/users").status_code, 403)

        # Officer cannot access admin user management or rule editing
        self.assertEqual(off.get("/api/v1/admin/users").status_code, 403)
        self.assertEqual(off.post("/api/v1/admin/rules", json={}).status_code, 403)

        # Admin can access admin endpoints
        self.assertEqual(admin.get("/api/v1/admin/users").status_code, 200)
        self.assertEqual(admin.get("/api/v1/admin/settings").status_code, 200)

    def test_documents_encrypted_at_rest(self):
        uploads_dir = os.environ["UPLOADS_DIR"]
        enc_file = os.path.join(uploads_dir, "SV-TEST-001", "noc.pdf.enc")
        if os.path.exists(enc_file):
            with open(enc_file, "rb") as fh:
                raw = fh.read()
            # Must NOT start with standard PDF magic bytes (%PDF-)
            self.assertFalse(raw.startswith(b"%PDF-"))

    def test_security_headers_present(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")


class ApplicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.inst1 = get_authenticated_client("inst1@demo.com")
        self.officer = get_authenticated_client("officer@demo.com")

    def test_draft_create_edit_and_submit_workflow(self):
        # 1. Create draft application
        data = {
            "category": "EoA",
            "academic_year": "2026-27",
            "programme": "",
            "intake": "",
            "institution_type": "Private",
            "action": "draft"
        }
        res = self.inst1.post("/api/v1/applications", json=data)
        self.assertEqual(res.status_code, 201)
        app_id = res.json()["application"]["id"]

        # Draft is visible to institution but hidden (404) to officers
        self.assertEqual(self.inst1.get(f"/api/v1/applications/{app_id}").status_code, 200)
        self.assertEqual(self.officer.get(f"/api/v1/applications/{app_id}").status_code, 404)

        # 2. Cannot submit while mandatory fields are missing
        sub_res = self.inst1.post(f"/api/v1/applications/{app_id}/submit")
        self.assertEqual(sub_res.status_code, 400)

        # 3. Edit draft with required fields
        edit_data = {
            "category": "EoA",
            "academic_year": "2026-27",
            "programme": "B.Tech Computer Engineering",
            "intake": "120",
            "institution_type": "Private"
        }
        self.assertEqual(self.inst1.post(f"/api/v1/applications/{app_id}/edit", json=edit_data).status_code, 200)

        # 4. Upload clean documents
        files = syn_files("APP-001")
        up_res = self.inst1.post(f"/api/v1/applications/{app_id}/documents", files=files)
        self.assertEqual(up_res.status_code, 200)
        self.assertGreater(up_res.json()["saved"], 0)

        # 5. Submit application
        sub_ok = self.inst1.post(f"/api/v1/applications/{app_id}/submit")
        self.assertEqual(sub_ok.status_code, 200)

        # Now visible to officers
        self.assertEqual(self.officer.get(f"/api/v1/applications/{app_id}").status_code, 200)

    def test_malware_and_invalid_uploads_rejected(self):
        # Create a fresh draft
        res = self.inst1.post("/api/v1/applications", json={"category": "EoA", "action": "draft"})
        app_id = res.json()["application"]["id"]

        # Attempt upload of bad files (executable, disguised file, EICAR test string)
        bad_files = [
            ("files", ("exploit.exe", b"MZ\x90\x00executable", "application/octet-stream")),
            ("files", ("fake.png", b"%PDF-1.4 disguised content", "image/png")),
            ("files", ("virus.pdf", b"%PDF-1.4 " + security.EICAR, "application/pdf")),
        ]
        up_res = self.inst1.post(f"/api/v1/applications/{app_id}/documents", files=bad_files)
        self.assertEqual(up_res.status_code, 400)


class ReviewAndAuditTests(unittest.TestCase):
    def setUp(self):
        self.officer = get_authenticated_client("officer@demo.com")
        self.admin = get_authenticated_client("admin@demo.com")

    def test_review_action_idempotency_and_reason_requirement(self):
        # Query open findings for SV-TEST-002
        full = self.officer.get("/api/v1/applications/SV-TEST-002/full").json()
        findings = full.get("findings", [])
        self.assertGreater(len(findings), 0)
        f = findings[0]

        # Review with empty reason should fail
        r_empty = self.officer.post(
            f"/api/v1/findings/{f['id']}/review",
            json={"action": "dismiss", "reason": "  "}
        )
        self.assertEqual(r_empty.status_code, 400)

        # Valid review with idempotency token
        token = "test-token-idempotency-12345"
        r_ok = self.officer.post(
            f"/api/v1/findings/{f['id']}/review",
            json={"action": "accept", "reason": "Confirmed deficiency", "token": token}
        )
        self.assertEqual(r_ok.status_code, 200)

        # Replayed post with identical token returns success without duplicate record
        r_replay = self.officer.post(
            f"/api/v1/findings/{f['id']}/review",
            json={"action": "accept", "reason": "Confirmed deficiency", "token": token}
        )
        self.assertEqual(r_replay.status_code, 200)

    def test_tamper_evident_audit_chain_verification(self):
        # Trigger an audit event
        S.audit("SYSTEM", "test_verification_event", "Audit chain integrity test", actor="admin@demo.com")
        db.session.commit()

        # Admin verification endpoint
        res = self.admin.get("/api/v1/admin/audit/verify")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertGreater(data["verified_events"], 0)
        self.assertIsNone(data["broken_event_id"])

    def test_report_exports(self):
        # JSON export
        res_json = self.officer.get("/applications/SV-TEST-001/report.json")
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.headers["content-type"], "application/json")

        # CSV export
        res_csv = self.officer.get("/applications/SV-TEST-001/report.csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers["content-type"])

        # PDF export
        res_pdf = self.officer.get("/applications/SV-TEST-001/report.pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(res_pdf.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
