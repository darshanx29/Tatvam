"""Unit tests for the deterministic core (no web layer).  python -m unittest discover -s tests"""
import io, os, sys, unittest
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import rules_engine as R, mock_issuer, security, anomaly, extractor, records
import pipeline

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(BASE, "data", "synthetic")
EVAL = datetime(2026, 10, 22)


def doc(name, dtype, **fields):
    return {"name": name, "doc_type": dtype, "ocr_method": "text_layer", "quality": None,
            "fields": {k: {"value": v, "confidence": 0.99, "page": 1} for k, v in fields.items()}}


APP = {"category": "EoA", "institution_id": "1-1001", "programme": "B.Tech Computer Engineering", "institution_type": "Private", "academic_year": "2026-27"}
RULES = R.load_rules()


class RuleTests(unittest.TestCase):
    def ids(self, docs, app=APP, rules=RULES, record=None):
        return [(f["rule_id"], f["status"]) for f in R.validate(app, docs, EVAL, rules, record)]

    def test_all_shipped_rules_are_valid(self):
        self.assertEqual([p for r in RULES for p in R.validate_definition(r)], [])

    def test_missing_required_documents(self):
        ids = self.ids([doc("a.pdf", "noc", institution_id="1-1001")])
        self.assertIn(("R-DOC-ACC", "FAIL"), ids)

    def test_expiry_boundary_valid_until_today_is_still_valid(self):
        d = [doc("c.pdf", "accreditation_certificate", valid_until="22-10-2026", institution_id="1-1001")]
        self.assertNotIn(("R-EXP-01", "FAIL"), self.ids(d))
        d = [doc("c.pdf", "accreditation_certificate", valid_until="21-10-2026", institution_id="1-1001")]
        self.assertIn(("R-EXP-01", "FAIL"), self.ids(d))

    def test_unparseable_date_is_inconclusive_not_a_crash(self):
        d = [doc("c.pdf", "noc", valid_until="31-02-2027")]
        self.assertIn(("R-EXP-01", "INCONCLUSIVE"), self.ids(d))

    def test_identifier_mismatch_and_cross_document(self):
        d = [doc("a.pdf", "noc", institution_id="1-9999", institution_name="X"), doc("b.pdf", "affidavit", institution_id="1-1001", institution_name="X")]
        ids = self.ids(d)
        self.assertIn(("R-ID-01", "FAIL"), ids); self.assertIn(("R-XDOC-01", "FAIL"), ids)

    def test_date_order(self):
        d = [doc("a.pdf", "noc", issue_date="10-05-2026", valid_until="01-01-2026")]
        self.assertIn(("R-DATE-01", "FAIL"), self.ids(d))

    def test_mandatory_field_blank(self):
        d = [doc("a.pdf", "noc", institution_id="1-1001")]          # issue_date missing
        self.assertIn(("R-FLD-01", "FAIL"), self.ids(d))

    def test_missing_identifier(self):
        self.assertIn(("R-ID-02", "FAIL"), self.ids([doc("a.pdf", "noc", institution_id="1-1001")]))

    def test_low_confidence_is_inconclusive(self):
        d = doc("a.pdf", "noc", institution_id="1-1001"); d["fields"]["institution_id"]["confidence"] = 0.5
        self.assertIn(("R-OCR-01", "INCONCLUSIVE"), self.ids([d]))

    def test_unreadable_flagged_but_not_for_photos(self):
        u = doc("scan.pdf", "unknown"); u["ocr_method"] = "unreadable"
        p = doc("lab.jpg", "infrastructure_photo"); p["ocr_method"] = "unreadable"
        ids = self.ids([u, p])
        self.assertEqual(ids.count(("R-OCR-02", "INCONCLUSIVE")), 1)

    def test_programme_and_intake_against_record(self):
        rec = records.get_record("1-1001")
        ok = doc("apr.pdf", "approval_record", programme="B.Tech Computer Engineering", approved_intake="120")
        bad = doc("apr.pdf", "approval_record", programme="B.Tech Computer Engineering", approved_intake="180")
        self.assertNotIn(("R-REC-03", "FAIL"), self.ids([ok], record=rec))
        self.assertIn(("R-REC-03", "FAIL"), self.ids([bad], record=rec))
        self.assertIn(("R-REC-03", "INCONCLUSIVE"), self.ids([ok], record=None))      # no record -> inconclusive, never a silent pass
        self.assertIn(("R-REC-02", "FAIL"), self.ids([ok], app={**APP, "programme": "Unknown Prog"}, record=rec))

    def test_infra_quality_is_advisory_inconclusive(self):
        p = doc("lab.jpg", "infrastructure_photo"); p["quality"] = {"issues": ["image appears blurred"]}
        self.assertIn(("R-INFRA-01", "INCONCLUSIVE"), self.ids([p]))
        p["quality"] = {"issues": []}
        self.assertNotIn(("R-INFRA-01", "INCONCLUSIVE"), self.ids([p]))

    def test_assess_includes_passes(self):
        res = R.assess(APP, [doc("a.pdf", "noc", institution_id="1-1001")], EVAL, RULES)
        self.assertTrue(any(x["status"] == "PASS" for x in res))

    def test_conditional_rule_applies_when(self):
        r = {"id": "R-C", "version": "1.0", "title": "t", "type": "required_doc", "doc_type": "floor_plan", "categories": ["EoA"], "severity": "low",
             "remedy": "x", "applies_when": {"institution_type": ["Autonomous"]}, "active": True}
        self.assertEqual(self.ids([], rules=[r]), [])
        self.assertEqual(self.ids([], app={**APP, "institution_type": "Autonomous"}, rules=[r]), [("R-C", "FAIL")])

    def test_versions_effective_dates(self):
        v1 = {**RULES[0], "version": "1.0", "effective_from": "2026-01-01", "effective_to": "2026-06-30"}
        v2 = {**RULES[0], "version": "1.1", "effective_from": "2026-07-01", "effective_to": None}
        self.assertEqual(R.select_versions([v1, v2], datetime(2026, 3, 1))[0]["version"], "1.0")
        self.assertEqual(R.select_versions([v1, v2], datetime(2026, 10, 1))[0]["version"], "1.1")
        self.assertEqual(R.select_versions([v1, v2], datetime(2025, 12, 1)), [])
        self.assertEqual(R.select_versions([v1, {**v2, "active": False}], datetime(2026, 10, 1)), [])

    def test_validate_definition_rejects_bad_rules(self):
        self.assertTrue(R.validate_definition({"id": "x"}))
        self.assertTrue(any("unknown type" in p for p in R.validate_definition({**RULES[0], "type": "nope"})))
        self.assertTrue(any("effective_from" in p for p in R.validate_definition({**RULES[0], "effective_from": "01-01-2026"})))


class IssuerTests(unittest.TestCase):
    F = lambda s, ref, iid="1-1001", vu="31-12-2028": {"certificate_no": {"value": ref}, "institution_id": {"value": iid}, "valid_until": {"value": vu}}
    REG = {"OK-1": {"institution_id": "1-1001", "valid_until": "31-12-2028"}, "OLD-1": {"institution_id": "1-1001", "valid_until": "01-01-2020"}}

    def v(self, f, attempt=1):
        return mock_issuer.verify(f, EVAL, registry=self.REG, attempt=attempt)["status"]

    def test_statuses(self):
        self.assertEqual(self.v(self.F("OK-1")), "verified")
        self.assertEqual(self.v(self.F("OK-1", iid="1-2")), "mismatch_detected")
        self.assertEqual(self.v(self.F("OLD-1", vu="01-01-2020")), "expired")
        self.assertEqual(self.v(self.F("PENDING-9")), "pending")
        self.assertEqual(self.v(self.F("UNAVAIL-9")), "source_unavailable")
        self.assertEqual(self.v(self.F("NOPE")), "manual_review_required")
        self.assertEqual(self.v({}), "manual_review_required")

    def test_outage_is_not_a_mismatch_and_flaky_recovers(self):
        self.assertEqual(self.v(self.F("FLAKY-1"), 1), "source_unavailable")
        self.assertEqual(self.v(self.F("FLAKY-1"), 2), "manual_review_required")       # reached the source; not in registry


class SecurityTests(unittest.TestCase):
    PDF = b"%PDF-1.4\n/Type /Page\n%%EOF"

    def test_upload_validation(self):
        self.assertTrue(security.validate_upload("a.pdf", self.PDF)[0])
        self.assertFalse(security.validate_upload("a.exe", b"MZ")[0])
        self.assertFalse(security.validate_upload("a.png", self.PDF)[0])              # content != extension
        self.assertFalse(security.validate_upload("a.pdf", b"")[0])
        self.assertFalse(security.validate_upload("a.pdf", b"%PDF-1.4 " + security.EICAR)[0])
        self.assertFalse(security.validate_upload("a.pdf", b"%PDF-1.4\n/Encrypt")[0])
        self.assertFalse(security.validate_upload("a.png", b"\x89PNG\r\n\x1a\nnot really")[0])

    def test_password_policy(self):
        self.assertIsNotNone(security.password_problem("short1A"))
        self.assertIsNotNone(security.password_problem("alllowercase123"))
        self.assertIsNone(security.password_problem("GoodPassw0rd!"))

    def test_ssrf_guard(self):
        self.assertFalse(security.validate_outbound_url("http://verify.gov.in/x", ["verify.gov.in"])[0])           # not https
        self.assertFalse(security.validate_outbound_url("https://evil.com/x", ["verify.gov.in"])[0])               # not allow-listed
        self.assertFalse(security.validate_outbound_url("https://localhost/x", ["localhost"])[0])                  # resolves to loopback
        self.assertFalse(security.validate_outbound_url("https://127.0.0.1/x", ["127.0.0.1"])[0])
        self.assertFalse(security.validate_outbound_url("https://user:pw@verify.gov.in/x", ["verify.gov.in"])[0])
        self.assertTrue(security.host_allowed("https://sub.verify.gov.in/a", ["verify.gov.in"]))
        self.assertFalse(security.host_allowed("https://verify.gov.in.evil.com/a", ["verify.gov.in"]))

    def test_csrf_compare(self):
        self.assertTrue(security.csrf_ok("abc", "abc")); self.assertFalse(security.csrf_ok("abc", "abd")); self.assertFalse(security.csrf_ok("abc", None))


class AnomalyTests(unittest.TestCase):
    def test_metadata_flags_on_edited_pdf(self):
        fl = anomaly.metadata_flags(os.path.join(SYN, "APP-002", "infra_fire.pdf"))
        self.assertTrue(any("editing tool" in f for f in fl)); self.assertTrue(any("after creation" in f for f in fl))
        self.assertEqual(anomaly.metadata_flags(os.path.join(SYN, "APP-001", "noc.pdf")), [])

    def test_structure_flags(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
            t.write(b"%PDF-1.4\n%%EOF\nxx\n%%EOF\n/JavaScript"); p = t.name
        fl = anomaly.structure_flags(p); os.unlink(p)
        self.assertTrue(any("end-of-file" in f for f in fl)); self.assertTrue(any("JavaScript" in f for f in fl))
        self.assertEqual(anomaly.structure_flags(os.path.join(SYN, "APP-001", "noc.pdf")), [])

    def test_phash_roundtrip_and_distance(self):
        a = anomaly.page_hashes(os.path.join(SYN, "APP-001", "noc.pdf"))
        self.assertEqual(anomaly.hamming(a, anomaly.hashes_from_str(anomaly.hashes_to_str(a))), 0)

    def test_duplicate_detection(self):
        d = {"name": "a", "sha": "x", "phashes": [], "text": "t"}
        self.assertEqual(len(anomaly.duplicate_flags([d, {**d, "name": "b"}])), 1)
        self.assertEqual(anomaly.duplicate_flags([d, {**d, "name": "b", "sha": "y", "text": "zzz"}]), [])

    def test_ela_is_off_by_default(self):
        self.assertIsNone(anomaly.ela_flag(os.path.join(SYN, "APP-004", "accreditation.jpg")))


class ExtractorTests(unittest.TestCase):
    def test_ocr_image_fields_have_confidence_and_location(self):
        ex = extractor.extract_pages(os.path.join(SYN, "APP-003", "noc.png"))
        self.assertEqual(ex["method"], "ocr_tesseract"); self.assertGreater(ex["mean_conf"], 0.7)
        f = extractor.extract_fields(ex["pages"], ex["method"])
        self.assertEqual(f["institution_id"]["value"], "1-3003")
        self.assertIsNotNone(f["institution_id"]["bbox"]); self.assertGreater(f["institution_id"]["confidence"], 0.5)

    def test_classification_and_unknown(self):
        self.assertEqual(extractor.classify("EXTENSION OF APPROVAL RECORD\nApproved Intake 120")[0], "approval_record")
        self.assertEqual(extractor.classify("lorem ipsum")[0], "unknown")

    def test_unreadable_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
            t.write(b"not an image"); p = t.name
        self.assertEqual(extractor.extract_pages(p)["method"], "unreadable"); os.unlink(p)


class PipelineTests(unittest.TestCase):
    def run_app(self, name, iid, **extra):
        return pipeline.process(os.path.join(SYN, name), "EoA", iid, eval_date=EVAL, app_extra=extra)

    def test_clean_application_is_preliminary_pass(self):
        rep = self.run_app("APP-001", "1-1001", programme="B.Tech Computer Engineering")
        self.assertEqual(rep["status"], "PRELIMINARY_PASS"); self.assertEqual(rep["findings"], []); self.assertEqual(rep["anomalies"], [])
        self.assertTrue(all(v["status"] == "verified" for v in rep["verifications"]))

    def test_problem_application_findings(self):
        rep = self.run_app("APP-002", "1-2002")
        ids = {f["rule_id"] for f in rep["findings"]}
        self.assertTrue({"R-DOC-AFF", "R-EXP-01", "R-ID-01", "R-DATE-01", "R-XDOC-01", "R-REC-03"} <= ids)
        self.assertEqual({v["status"] for v in rep["verifications"]}, {"expired", "source_unavailable", "mismatch_detected"})
        self.assertTrue(any(a["type"] == "duplicate" for a in rep["anomalies"]))
        self.assertTrue(all(a["note"].startswith("Preliminary") for a in rep["anomalies"]))        # never declared forgery
        for f in rep["findings"]:
            for k in ("rule_id", "observed", "expected", "source", "severity", "next_step", "rule_version"):
                self.assertIn(k, f)

    def test_correction_overrides_survive(self):
        rep = pipeline.process(os.path.join(SYN, "APP-002"), "EoA", "1-2002", eval_date=EVAL, overrides={("noc.pdf", "institution_id"): "1-2002", ("noc_copy.pdf", "institution_id"): "1-2002"})
        self.assertNotIn("R-ID-01", {f["rule_id"] for f in rep["findings"]})

    def test_cross_institution_reuse_flagged_but_same_institution_not(self):
        sha = anomaly.sha256(os.path.join(SYN, "APP-001", "noc.pdf"))
        other = [{"app_id": "X", "name": "n.pdf", "sha": sha, "cert_no": None, "institution_id": "9-9"}]
        rep = pipeline.process(os.path.join(SYN, "APP-001"), "EoA", "1-1001", eval_date=EVAL, other_docs=other, app_extra={"programme": "B.Tech Computer Engineering"})
        self.assertTrue(any(a["type"] == "duplicate_cross" for a in rep["anomalies"]))
        other[0]["institution_id"] = "1-1001"
        rep = pipeline.process(os.path.join(SYN, "APP-001"), "EoA", "1-1001", eval_date=EVAL, other_docs=other, app_extra={"programme": "B.Tech Computer Engineering"})
        self.assertFalse(any(a["type"] == "duplicate_cross" for a in rep["anomalies"]))

    def test_scanned_image_application_and_unusable_photo(self):
        rep = self.run_app("APP-003", "1-3003", programme="B.Tech Civil Engineering")
        self.assertEqual([f["rule_id"] for f in rep["findings"]], ["R-INFRA-01"])
        self.assertTrue(all(d["ocr_method"] == "ocr_tesseract" for d in rep["documents"] if d["name"].endswith(".png")))

class EoaExtractionTests(unittest.TestCase):
    TEXT = ("All India Council for Technical Education\nExtension of Approval (EoA) for the Academic Year 2025-26\n"
            "Permanent Id : 1-3634834011\nApplication Id : 1-44638744438\nName of the Institution : L M Thapar School of Management\n"
            "Region : North-West\nInstitution Type : Institution Deemed to be University (Pvt)\nYear of Establishment : 2007\n"
            "Approval Date : 03-Jan-2025\n")

    def test_structured_eoa_summary(self):
        dtype, _ = extractor.classify(self.TEXT, "eoa.pdf")
        rows = extractor.eoa_summary(dtype, extractor.extract_fields([{"text": self.TEXT, "words": []}], "text_layer"))
        self.assertEqual([(l, v) for l, v, _ in rows], [
            ("Document category", "Extension of Approval (EoA)"), ("Institution", "L M Thapar School of Management"),
            ("Permanent ID", "1-3634834011"), ("Application ID", "1-44638744438"), ("Region", "North-West"),
            ("Institution type", "Institution Deemed to be University (Pvt)"), ("Establishment year", "2007"),
            ("Approval date", "03-Jan-2025"), ("Academic year", "2025-26")])

    def test_eoa_feeds_existing_rules_and_missing_field_is_visible(self):
        f = extractor.extract_fields([{"text": self.TEXT, "words": []}], "text_layer")
        self.assertEqual((f["institution_id"]["value"], f["issue_date"]["value"]), ("1-3634834011", "03-01-2025"))
        rows = extractor.eoa_summary("approval_record", {k: v for k, v in f.items() if k != "region"})
        self.assertIsNone(dict((l, v) for l, v, _ in rows)["Region"])
        self.assertEqual(extractor.eoa_summary("noc", f), [])


if __name__ == "__main__":
    unittest.main()


class EoaReviewTests(unittest.TestCase):
    FULL = dict(institution_name="L M Thapar School of Management", permanent_id="1-3634834011", application_id="1-44638744438",
                region="North-West", institution_type="Institution Deemed to be University (Pvt)", establishment_year="2007",
                approval_date="03-Jan-2025", academic_year="2025\u201326", institution_id="1-3634834011", issue_date="03-01-2025")

    def ids(self, **fields):
        d = [doc("eoa.pdf", "approval_record", **fields)]
        app = {**APP, "institution_id": "1-3634834011"}
        return [(f["rule_id"], f["status"]) for f in R.validate(app, d, EVAL, RULES, None)]

    def test_past_academic_year_is_flagged_expired_not_missing(self):
        ids = self.ids(**self.FULL)
        self.assertIn(("R-EOA-EXP-01", "FAIL"), ids)
        self.assertNotIn(("R-EOA-FLD-01", "FAIL"), ids)
        self.assertNotIn(("R-ID-02", "FAIL"), ids)          # Permanent/Application ID is the EoA's identifier
        self.assertNotIn(("R-FLD-01", "FAIL"), ids)

    def test_current_academic_year_not_expired_and_missing_fields_listed(self):
        f = {**self.FULL, "academic_year": "2026-27"}; del f["region"]
        ids = self.ids(**f)
        self.assertNotIn(("R-EOA-EXP-01", "FAIL"), ids)
        self.assertIn(("R-EOA-FLD-01", "FAIL"), ids)

    def test_old_format_approval_record_is_not_held_to_eoa_rules(self):
        ids = self.ids(institution_id="1-3634834011", issue_date="01-06-2025", certificate_no="EOA-1")
        self.assertNotIn(("R-EOA-FLD-01", "FAIL"), ids)

    def test_review_lists_every_field_with_status(self):
        f = {k: {"value": v, "confidence": 0.95} for k, v in self.FULL.items()}; del f["region"]
        finds = [{"status": "FAIL", "title": "EoA academic year must not have ended", "reason": "Expired: academic year 2025\u201326 ended on 30-06-2026"}]
        rv = extractor.eoa_review("approval_record", f, finds)
        st = {r["label"]: r["status"] for r in rv["rows"]}
        self.assertEqual((st["Region"], st["Academic year"], st["Permanent ID"]), ("Missing", "Expired", "Found"))
        self.assertEqual(rv["headline"], "Expired")
        self.assertIsNone(extractor.eoa_review("noc", f))


class DocumentReviewTests(unittest.TestCase):
    def review(self, dtype, registry=None, **fields):
        from core import docreview
        f = {k: {"value": v, "confidence": 0.95, "page": 1} for k, v in fields.items()}
        d = [{"name": "x.pdf", "doc_type": dtype, "ocr_method": "text_layer", "quality": None, "fields": f, "text": ""}]
        res = [x for x in R.assess(APP, d, EVAL, RULES, None) if x["source"] == "x.pdf"]
        return docreview.review(dtype, f, res, mock_issuer.verify(f, EVAL, registry=registry or {}), [])

    def status(self, rv):
        return {r["label"]: r["status"] for r in rv["rows"]}

    def test_expired_mismatched_and_missing_are_each_marked_on_their_field(self):
        rv = self.review("noc", {"NOC-1": {"institution_id": "1-1001", "valid_until": "31-12-2027"}},
                         institution_name="X College", institution_id="1-2999", certificate_no="NOC-1", issue_date="10-02-2026", valid_until="31-12-2025")
        st = self.status(rv)
        self.assertEqual((st["Institution ID"], st["Valid until"], st["Issued by"]), ("Mismatch", "Expired", "Missing"))
        self.assertEqual(st["Certificate / reference no."], "Mismatch")      # source registry disagrees with the document
        self.assertIn("expired", rv["headline"]); self.assertEqual(rv["level"], "bad")

    def test_clean_document_is_all_found(self):
        rv = self.review("noc", {"NOC-1": {"institution_id": "1-1001", "valid_until": "31-12-2027"}}, institution_name="Demo Institute of Technology",
                         institution_id="1-1001", certificate_no="NOC-1", issued_by="State", issue_date="10-02-2026", valid_until="31-12-2027")
        self.assertEqual(rv["headline"], "All checks passed")
        self.assertEqual(self.status(rv)["Source verification"], "Verified")

    def test_unreadable_document_says_so(self):
        rv = self.review("affidavit")
        self.assertTrue(any("No fields could be read" in a["text"] for a in rv["alerts"]))
        self.assertIn("missing", rv["headline"])

    def test_text_pairs_list_what_was_read(self):
        self.assertEqual(extractor.text_pairs("Region : North-West\nnot a pair\nYear of Establishment - 2007"),
                         [("Region", "North-West"), ("Year of Establishment", "2007")])
