"""Workflow / security tests through the Flask test client.  python -m unittest discover -s tests"""
import io, json, os, re, shutil, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-secret")
_tmp = tempfile.mkdtemp(prefix="svtest_")
os.environ["DOC_ENCRYPTION_KEY"] = "ZmFrZWtleWZha2VrZXlmYWtla2V5ZmFrZWtleTEyMzQ="       # 32 url-safe base64 bytes
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "t.db")

import app as appmod
from models import *
import services as S

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(BASE, "data", "synthetic")
APP = appmod.create_app({"UPLOADS": os.path.join(_tmp, "uploads"), "ASYNC_PROCESSING": False, "TESTING": True})


def setUpModule():
    appmod.seed(APP)


def tearDownModule():
    shutil.rmtree(_tmp, ignore_errors=True)


def token(c, url="/login"):
    m = re.search(r'name="csrf_token" value="([^"]+)"', c.get(url).text)
    return m.group(1) if m else c.get("/api/v1/me").get_json()["csrf_token"]        # page without a form: ask the API


def login(email, pw="demo123"):
    c = APP.test_client()
    r = c.post("/login", data={"email": email, "password": pw, "csrf_token": token(c)})
    assert r.status_code == 302, (email, r.status_code)
    return c


def files(src, names=None):
    d = os.path.join(SYN, src)
    return [(io.BytesIO(open(os.path.join(d, n), "rb").read()), n) for n in sorted(names or os.listdir(d))]


def make_app(c, src, submit=True, prog="B.Tech Mechanical Engineering", intake="120", itype="Autonomous", names=None):
    data = {"csrf_token": token(c, "/applications/new"), "category": "EoA", "academic_year": "2026-27", "programme": prog, "intake": intake,
            "institution_type": itype, "action": "submit" if submit else "draft", "files": files(src, names)}
    r = c.post("/applications/new", data=data, content_type="multipart/form-data")
    assert r.status_code == 302, r.status_code
    return r.headers["Location"].rsplit("/", 1)[1]


def post(c, url, page="/dashboard", **data):
    return c.post(url, data={"csrf_token": token(c, page), **data})


def q(model, **kw):
    with APP.app_context():
        return model.query.filter_by(**kw).all()


class AccessTests(unittest.TestCase):
    def test_csrf_required(self):
        c = APP.test_client(); c.get("/login")
        self.assertEqual(c.post("/login", data={"email": "officer@demo.com", "password": "demo123"}).status_code, 400)

    def test_wrong_password_and_throttle(self):
        c = APP.test_client()
        for _ in range(5):
            r = c.post("/login", data={"email": "thr@demo.com", "password": "x", "csrf_token": token(c)})
            self.assertEqual(r.status_code, 200)
        self.assertEqual(c.post("/login", data={"email": "thr@demo.com", "password": "x", "csrf_token": token(c)}).status_code, 429)

    def test_unauthenticated_redirect_and_api_401(self):
        c = APP.test_client()
        self.assertEqual(c.get("/dashboard").status_code, 302)
        self.assertEqual(c.get("/api/v1/applications").status_code, 401)

    def test_institution_isolation(self):
        i1, off = login("inst1@demo.com"), login("officer@demo.com")
        self.assertEqual(i1.get("/applications/SV-TEST-002").status_code, 403)
        self.assertEqual(i1.get("/applications/SV-TEST-001").status_code, 200)
        self.assertEqual(i1.get("/api/v1/applications/SV-TEST-002/findings").status_code, 403)
        self.assertEqual(i1.get("/documents/1").status_code in (200, 403), True)
        did = q(Document, app_id="SV-TEST-002")[0].id
        self.assertEqual(i1.get(f"/documents/{did}/file").status_code, 403)
        self.assertEqual(off.get(f"/documents/{did}/file").status_code, 200)

    def test_role_enforcement(self):
        i1, off = login("inst1@demo.com"), login("officer@demo.com")
        fid = q(Finding, app_id="SV-TEST-002")[0].id
        self.assertEqual(i1.post(f"/findings/{fid}/review", data={"csrf_token": token(i1, "/dashboard"), "action": "accept", "reason": "x"}).status_code, 403)
        self.assertEqual(off.get("/admin/rules").status_code, 403)
        self.assertEqual(i1.get("/api/v1/rules").status_code, 403)

    def test_files_encrypted_at_rest(self):
        raw = open(os.path.join(APP.config["UPLOADS"], "SV-TEST-001", "noc.pdf.enc"), "rb").read()
        self.assertFalse(raw.startswith(b"%PDF"))

    def test_security_headers(self):
        h = login("officer@demo.com").get("/dashboard").headers
        self.assertEqual(h["X-Content-Type-Options"], "nosniff"); self.assertEqual(h["Cache-Control"], "no-store")


class IntakeTests(unittest.TestCase):
    def test_draft_edit_submit_flow(self):
        c, off = login("inst1@demo.com"), login("officer@demo.com")
        aid = make_app(c, "APP-001", submit=False, prog="", intake="", names=["noc.pdf"])
        self.assertEqual(q(Application, id=aid)[0].status, "Draft")
        self.assertEqual(off.get(f"/applications/{aid}").status_code, 404)                          # drafts invisible to officers
        r = post(c, f"/applications/{aid}/submit", f"/applications/{aid}")
        self.assertEqual(q(Application, id=aid)[0].status, "Draft")                                 # mandatory fields missing
        post(c, f"/applications/{aid}/edit", f"/applications/{aid}", category="EoA", academic_year="2026-27", programme="B.Tech Computer Engineering", intake="120", institution_type="Private")
        self.assertEqual(len(q(ApplicationVersion, app_id=aid)), 2)                                 # version history kept
        c.post(f"/applications/{aid}/upload", data={"csrf_token": token(c, f"/applications/{aid}"), "files": files("APP-001", ["accreditation.pdf", "affidavit.pdf", "approval_record.pdf", "infra_fire.pdf"])}, content_type="multipart/form-data")
        post(c, f"/applications/{aid}/submit", f"/applications/{aid}")
        a = q(Application, id=aid)[0]
        self.assertEqual(a.status, "Preliminary checks complete")
        self.assertEqual([f for f in q(Finding, app_id=aid) if f.state != "resolved"], [])

    def test_upload_rejections_are_logged(self):
        c = login("inst1@demo.com")
        aid = make_app(c, "APP-001", submit=False, names=["noc.pdf"])
        bad = [(io.BytesIO(b"MZ\x90"), "evil.exe"), (io.BytesIO(b"%PDF-1.4 fake"), "fake.png"), (io.BytesIO(b"%PDF-1.4 " + __import__("core.security", fromlist=["x"]).EICAR), "virus.pdf")]
        c.post(f"/applications/{aid}/upload", data={"csrf_token": token(c, f"/applications/{aid}"), "files": bad}, content_type="multipart/form-data")
        with APP.app_context():
            self.assertEqual(AuditEvent.query.filter_by(app_id=aid, event="upload_rejected").count(), 3)
            self.assertEqual(Application.query.get(aid).status, "Draft")
        self.assertEqual(S.EncryptedLocalStorage(APP.config["UPLOADS"]).names(aid), ["noc.pdf"])

    def test_missing_document_findings_for_incomplete_application(self):
        c = login("inst3@demo.com")
        aid = make_app(c, "APP-004", prog="B.Tech Civil Engineering", itype="Private")
        rules = {f.rule_id for f in q(Finding, app_id=aid)}
        self.assertEqual(rules, {"R-DOC-NOC", "R-DOC-AFF", "R-DOC-APR", "R-DOC-INF"})


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.inst, self.off, self.ver = login("inst2@demo.com"), login("officer@demo.com"), login("verifier@demo.com")
        self.aid = make_app(self.inst, "APP-002")

    def findings(self, **kw):
        return [f for f in q(Finding, app_id=self.aid, **kw) if f.state != "resolved"]

    def test_review_idempotent_and_reason_mandatory(self):
        f = [x for x in self.findings() if x.rule_id == "R-DATE-01"][0]
        r = post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="dismiss", reason="  ", token="t1")
        self.assertEqual(q(Finding, id=f.id)[0].state, "open")
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="accept", reason="confirmed", token="t2")
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="dismiss", reason="replay", token="t2")           # same token: ignored
        self.assertEqual(q(Finding, id=f.id)[0].state, "accepted")
        self.assertEqual(len(q(ReviewAction, token="t2")), 1)

    def test_high_severity_dismissal_logged_as_override(self):
        f = [x for x in self.findings() if x.severity == "high"][0]
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="dismiss", reason="issuer confirmed by phone", token="ov1")
        self.assertEqual(len(q(AuditEvent, app_id=self.aid, event="override_logged")), 1)

    def test_request_evidence_notifies_institution_and_sets_action_required(self):
        f = [x for x in self.findings() if x.rule_id == "R-DOC-AFF"][0]
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="request_evidence", reason="Upload the affidavit", token="re1")
        self.assertEqual(q(Application, id=self.aid)[0].status, "Action required")
        self.assertEqual(len(q(Notification, app_id=self.aid)), 1)
        self.assertIn("Upload the affidavit", self.inst.get("/dashboard").text)
        post(self.inst, f"/findings/{f.id}/respond", f"/applications/{self.aid}", text="Uploading today", token="rs1")
        self.assertEqual(len(q(ReviewAction, app_id=self.aid, action="institution_response")), 1)

    def test_rectification_upload_resolves_finding_and_keeps_history(self):
        f = [x for x in self.findings() if x.rule_id == "R-DOC-AFF"][0]
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="accept", reason="noted", token="rc1")
        self.inst.post(f"/applications/{self.aid}/upload", data={"csrf_token": token(self.inst, f"/applications/{self.aid}"), "files": files("APP-001", ["affidavit.pdf"])}, content_type="multipart/form-data")
        again = q(Finding, id=f.id)[0]
        self.assertEqual(again.state, "resolved")                                          # no longer reproduced
        self.assertEqual(len(q(ReviewAction, finding_id=f.id)), 1)                         # decision history preserved

    def test_decisions_survive_a_rerun(self):
        f = [x for x in self.findings() if x.rule_id == "R-ID-01"][0]
        post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="escalate", reason="check", token="sv1")
        post(self.off, f"/applications/{self.aid}/validate", f"/applications/{self.aid}")
        self.assertEqual(q(Finding, id=f.id)[0].state, "escalated")

    def test_manual_verification_resolves_unavailable_source(self):
        v = [x for x in self.findings() if x.rule_id == "VER-SOURCE_UNAVAILABLE"][0]
        post(self.ver, f"/applications/{self.aid}/manual-verify", f"/applications/{self.aid}", document=v.source, outcome="verified", reference="CALL-1", note="Confirmed with Fire Dept by phone")
        self.assertEqual(q(Finding, id=v.id)[0].state, "resolved")
        vr = [r for r in q(VerificationRecord, app_id=self.aid) if r.manual][0]
        self.assertEqual((vr.verified_by, vr.status), ("verifier@demo.com", "verified"))

    def test_retry_is_bounded_by_policy(self):
        v = [x for x in self.findings() if x.rule_id == "VER-SOURCE_UNAVAILABLE"][0]
        for _ in range(6):
            post(self.ver, f"/applications/{self.aid}/reverify", f"/applications/{self.aid}", document=v.source)
        recs = [r for r in q(VerificationRecord, app_id=self.aid, doc_name=v.source) if not r.manual]
        self.assertEqual(max(r.attempt for r in recs), 3)

    def test_field_correction_reruns_checks_and_is_audited(self):
        with APP.app_context():
            doc = Document.query.filter_by(app_id=self.aid, name="noc.pdf").first()
            fid = next(f.id for f in doc.fields if f.name == "institution_id"); did = doc.id
        post(self.off, f"/fields/{fid}/correct", f"/documents/{did}", value="1-2002", reason="Typo on scan")
        with APP.app_context():
            f = ExtractedField.query.get(fid)
            self.assertEqual((f.value, f.original_value, f.corrected_by), ("1-2002", "1-2999", "officer@demo.com"))
        offending = [x for x in self.findings() if x.rule_id == "R-ID-01" and x.source == "noc.pdf"]
        self.assertEqual(offending, [])
        self.assertTrue(q(AuditEvent, app_id=self.aid, event="field_corrected"))

    def test_close_requires_recommendation_and_no_open_findings(self):
        r = post(self.off, f"/applications/{self.aid}/close", f"/applications/{self.aid}")
        self.assertNotEqual(q(Application, id=self.aid)[0].status, "Closed in prototype")
        for f in self.findings():
            post(self.off, f"/findings/{f.id}/review", f"/applications/{self.aid}", action="accept", reason="reviewed", token=f"cl{f.id}")
        post(self.off, f"/applications/{self.aid}/recommendation", f"/applications/{self.aid}", choice="request_rectification", note="see findings", token="rec1")
        post(self.off, f"/applications/{self.aid}/close", f"/applications/{self.aid}")
        self.assertEqual(q(Application, id=self.aid)[0].status, "Closed in prototype")


class ExportAndDashboardTests(unittest.TestCase):
    def test_exports_and_audit(self):
        off = login("officer@demo.com")
        pdf = off.get("/applications/SV-TEST-002/report.pdf"); self.assertTrue(pdf.data.startswith(b"%PDF"))
        csv = off.get("/applications/SV-TEST-002/report.csv").text; self.assertIn("rule_id", csv)
        js = json.loads(off.get("/applications/SV-TEST-002/report.json").text); self.assertIn("disclaimer", js); self.assertTrue(js["assessment"])
        self.assertTrue(q(AuditEvent, app_id="SV-TEST-002", event="report_exported"))

    def test_institution_report_hides_officer_only_detail(self):
        inst = login("inst2@demo.com")
        self.assertNotIn("private_detail", inst.get("/applications/SV-TEST-002/report.json").text)

    def test_dashboard_kpis_and_compliance_screen(self):
        off = login("officer@demo.com")
        t = off.get("/dashboard").text
        for s in ("Median processing time", "Usable verification responses", "% with missing docs"): self.assertIn(s, t)
        c = off.get("/applications/SV-TEST-002/compliance").text
        for s in ("Deficient", "Compliant", "R-REC-03"): self.assertIn(s, c)
        self.assertIn("Inspection / additional-evidence", off.get("/applications/SV-TEST-003/compliance").text)

    def test_document_viewer_page_image_and_bbox_overlay(self):
        off = login("officer@demo.com")
        did = q(Document, app_id="SV-TEST-003", name="noc.png")[0].id
        r = off.get(f"/documents/{did}"); self.assertEqual(r.status_code, 200); self.assertIn('id="box', r.text)
        self.assertEqual(off.get(f"/documents/{did}/page/1.png").mimetype, "image/png")


class AdminTests(unittest.TestCase):
    def test_rule_edit_creates_new_version_and_changes_behaviour(self):
        adm = login("admin@demo.com")
        with APP.app_context():
            d = RuleVersion.query.filter_by(rule_id="R-DATE-01").first().definition
        d["severity"] = "low"
        post(adm, "/admin/rules/R-DATE-01", "/admin/rules/R-DATE-01", definition=json.dumps(d), note="downgrade")
        with APP.app_context():
            vs = RuleVersion.query.filter_by(rule_id="R-DATE-01").order_by(RuleVersion.id).all()
            self.assertEqual([v.version for v in vs], ["1.0", "1.1"]); self.assertIsNotNone(vs[0].definition["effective_to"])
        off = login("officer@demo.com")
        post(off, "/applications/SV-TEST-002/validate", "/applications/SV-TEST-002")
        f = [x for x in q(Finding, app_id="SV-TEST-002") if x.rule_id == "R-DATE-01"][0]
        self.assertEqual((f.severity, f.rule_version), ("low", "1.1"))

    def test_invalid_rule_rejected(self):
        adm = login("admin@demo.com")
        r = post(adm, "/admin/rules/new", "/admin/rules/new", definition=json.dumps({"id": "R-BAD", "type": "nope"}))
        self.assertEqual(len(q(RuleVersion, rule_id="R-BAD")), 0)
        post(adm, "/admin/rules/new", "/admin/rules/new", definition="{not json")
        self.assertEqual(len(q(RuleVersion, rule_id="R-BAD")), 0)

    def test_user_creation_policy_and_revocation(self):
        adm = login("admin@demo.com")
        post(adm, "/admin/users", "/admin/users", email="weak@demo.com", role=SCRUTINY, password="weak")
        self.assertEqual(len(q(User, email="weak@demo.com")), 0)
        post(adm, "/admin/users", "/admin/users", email="new.officer@demo.com", role=SCRUTINY, password="StrongPass123", name="N")
        c = login("new.officer@demo.com", "StrongPass123")
        self.assertEqual(c.get("/dashboard").status_code, 200)
        uid = q(User, email="new.officer@demo.com")[0].id
        post(adm, f"/admin/users/{uid}/toggle", "/admin/users")
        self.assertEqual(c.get("/dashboard").status_code, 302)                              # live session revoked immediately

    def test_non_admin_cannot_create_users(self):
        off = login("officer@demo.com")
        self.assertEqual(off.post("/admin/users", data={"csrf_token": token(off, "/dashboard")}).status_code, 403)


class ApiTests(unittest.TestCase):
    def test_api_flow_and_csrf_header(self):
        c = login("inst1@demo.com")
        me = c.get("/api/v1/me").get_json(); h = {"X-CSRF-Token": me["csrf_token"]}
        self.assertEqual(c.post("/api/v1/applications", json={"category": "EoA"}).status_code, 400)           # no CSRF header
        r = c.post("/api/v1/applications", json={"category": "EoA", "academic_year": "2026-27", "programme": "B.Tech Computer Engineering", "intake": "120"}, headers=h)
        self.assertEqual(r.status_code, 201); aid = r.get_json()["id"]
        self.assertEqual(c.post(f"/api/v1/applications/{aid}/validate", headers=h).status_code, 409)         # draft
        up = c.post(f"/api/v1/applications/{aid}/documents", data={"files": files("APP-001")}, headers=h, content_type="multipart/form-data")
        self.assertEqual(up.get_json()["saved"], 5)
        cl = c.get(f"/api/v1/applications/{aid}/checklist").get_json()["items"]; self.assertTrue(all(not i["present"] for i in cl))     # not yet processed
        with APP.app_context():
            a = Application.query.get(aid); a.status = "Submitted"; db.session.commit()
        v = c.post(f"/api/v1/applications/{aid}/validate", headers=h); self.assertEqual(v.status_code, 202)
        self.assertEqual(c.get(f"/api/v1/applications/{aid}/status").get_json()["run"]["status"], "done")
        self.assertTrue(all(i["present"] for i in c.get(f"/api/v1/applications/{aid}/checklist").get_json()["items"]))
        self.assertEqual(c.get(f"/api/v1/applications/{aid}/findings").get_json()["items"], [])
        self.assertTrue(c.get(f"/api/v1/applications/{aid}/audit").get_json()["items"])
        self.assertEqual(c.get("/api/v1/applications").get_json()["items"][0]["institution_id"], "1-1001")

    def test_api_review_and_rules(self):
        off = login("officer@demo.com"); h = {"X-CSRF-Token": off.get("/api/v1/me").get_json()["csrf_token"]}
        fid = q(Finding, app_id="SV-TEST-004")[0].id
        self.assertEqual(off.post(f"/api/v1/findings/{fid}/review", json={"action": "accept"}, headers=h).status_code, 400)       # reason mandatory
        r = off.post(f"/api/v1/findings/{fid}/review", json={"action": "accept", "reason": "ok", "token": "api1"}, headers=h)
        self.assertEqual(r.get_json()["state"], "accepted")
        self.assertTrue(off.get("/api/v1/rules").get_json()["items"])


class AsyncAndRetentionTests(unittest.TestCase):
    def test_async_processing_with_progress(self):
        APP.config["ASYNC_PROCESSING"] = True
        try:
            c = login("inst1@demo.com"); aid = make_app(c, "APP-001", prog="B.Tech Computer Engineering", itype="Private")
            for _ in range(120):
                run = c.get(f"/api/v1/applications/{aid}/status").get_json()["run"]
                if run["status"] in ("done", "error"): break
                time.sleep(0.5)
            self.assertEqual(run["status"], "done", run)
            self.assertEqual(q(Application, id=aid)[0].status, "Preliminary checks complete")
        finally:
            APP.config["ASYNC_PROCESSING"] = False

    def test_processing_failure_never_leaves_application_stuck(self):
        c = login("inst1@demo.com"); aid = make_app(c, "APP-001", submit=False, names=["noc.pdf"], prog="B.Tech Computer Engineering", itype="Private")
        with APP.app_context():
            a = Application.query.get(aid); a.status = "Submitted"; db.session.commit()
            orig = S.pipeline.process
            S.pipeline.process = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
            try:
                S.queue_validation(Application.query.get(aid), async_ok=False)
            finally:
                S.pipeline.process = orig
            self.assertEqual(Application.query.get(aid).status, "Submitted")
            self.assertEqual(ProcessingRun.query.filter_by(app_id=aid).order_by(ProcessingRun.id.desc()).first().status, "error")

    def test_retention_purge_secure_deletes_closed_applications(self):
        from datetime import datetime, timedelta
        with APP.app_context():
            a = Application(id="SV-OLD", institution_id="1-1001", status="Closed in prototype", closed_at=datetime.now() - timedelta(days=800))
            db.session.add(a); db.session.commit()
            S.storage().save("SV-OLD", "x.pdf", b"%PDF-1.4"); self.assertEqual(S.storage().names("SV-OLD"), ["x.pdf"])
            appmod.purge(APP)
            self.assertEqual(S.storage().names("SV-OLD"), [])
            self.assertTrue(AuditEvent.query.filter_by(app_id="SV-OLD", event="retention_purge").count())


if __name__ == "__main__":
    unittest.main()
