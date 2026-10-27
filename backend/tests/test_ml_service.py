"""Unit tests for the modular AI/ML and deterministic analysis service (ml_service.py).
Tests document classification, multi-hash duplicates, cryptographic signature analysis,
and infrastructure computer vision.
"""
import io
import os
import sys
import unittest
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import ml_service

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(BASE, "data", "synthetic")


class MLClassifierTests(unittest.TestCase):
    def test_classification_known_categories(self):
        # 1. Approval record
        text_eoa = "All India Council for Technical Education Extension of Approval Approved Intake 120"
        dtype, conf, meta = ml_service.classify_document(text_eoa, filename="approval_record.pdf")
        self.assertEqual(dtype, "approval_record")
        self.assertGreater(conf, 0.70)
        self.assertIn("method", meta)
        self.assertTrue(len(meta["top_evidence"]) > 0)

        # 2. NOC
        text_noc = "Government of Maharashtra Department of Higher and Technical Education No Objection Certificate NOC"
        dtype, conf, meta = ml_service.classify_document(text_noc, filename="noc.pdf")
        self.assertEqual(dtype, "noc")
        self.assertGreater(conf, 0.70)

        # 3. Affidavit
        text_aff = "Before the Notary Public Solemnly Affirm and declare on oath Non-Judicial Stamp Paper Affidavit"
        dtype, conf, meta = ml_service.classify_document(text_aff, filename="affidavit.pdf")
        self.assertEqual(dtype, "affidavit")
        self.assertGreater(conf, 0.70)

        # 4. Accreditation certificate
        text_acc = "National Board of Accreditation NBA Tier-I Accredited Grade A+"
        dtype, conf, meta = ml_service.classify_document(text_acc, filename="accreditation.pdf")
        self.assertEqual(dtype, "accreditation_certificate")
        self.assertGreater(conf, 0.70)

        # 5. Infrastructure certificate
        text_fire = "Fire and Life Safety Certificate Structural Stability Soundness Building Safety"
        dtype, conf, meta = ml_service.classify_document(text_fire, filename="infra_fire.pdf")
        self.assertEqual(dtype, "infrastructure_certificate")
        self.assertGreater(conf, 0.70)

    def test_classification_unknown_noise(self):
        text_noise = "Random lorem ipsum text with no regulatory terms whatsoever 12345"
        dtype, conf, meta = ml_service.classify_document(text_noise, filename="random.pdf")
        self.assertEqual(dtype, "unknown")
        self.assertEqual(conf, 0.0)

    def test_classification_structural_heuristics(self):
        # Raster image with photo keyword
        dtype, conf, meta = ml_service.classify_document("", filename="campus_photo.jpg", is_raster_image=True)
        self.assertEqual(dtype, "infrastructure_photo")

        # High vector drawing ratio
        dtype, conf, meta = ml_service.classify_document("ground floor plan scale 1:100", filename="drawing.pdf", vector_drawing_ratio=0.6)
        self.assertEqual(dtype, "floor_plan")


class DuplicateAndSimilarityTests(unittest.TestCase):
    def test_sha256_computation(self):
        data = b"AICTE Document Verification Test Byte Stream"
        h1 = ml_service.compute_sha256(data)
        h2 = ml_service.compute_sha256(data)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_phash_and_dhash_sensitivity(self):
        # Create test image
        im1 = Image.new("RGB", (200, 200), color=(255, 255, 255))
        # Add diagonal line
        arr = np.array(im1)
        for i in range(100):
            arr[i, i] = [0, 0, 0]
        im1 = Image.fromarray(arr)

        # Identical image should have zero distance
        p1 = ml_service.compute_phash(im1)
        d1 = ml_service.compute_dhash(im1)

        p2 = ml_service.compute_phash(im1)
        d2 = ml_service.compute_dhash(im1)

        self.assertEqual(int(np.count_nonzero(p1 != p2)), 0)
        self.assertEqual(int(np.count_nonzero(d1 != d2)), 0)

        # Slightly resized image should retain low distance (<= 10 bits out of 64)
        im_resized = im1.resize((150, 150))
        p_resized = ml_service.compute_phash(im_resized)
        self.assertLessEqual(int(np.count_nonzero(p1 != p_resized)), 10)

    def test_text_similarity_metrics(self):
        t1 = "All India Council for Technical Education Extension of Approval for Academic Year 2026-27"
        t2 = "All India Council for Technical Education Extension of Approval for Academic Year 2026-27"
        sims = ml_service.compute_text_similarity(t1, t2)
        self.assertEqual(sims["jaccard"], 1.0)
        self.assertEqual(sims["cosine"], 1.0)
        self.assertEqual(sims["ratio"], 1.0)

        t3 = "Completely unrelated text about forestry and wildlife conservation"
        sims_diff = ml_service.compute_text_similarity(t1, t3)
        self.assertEqual(sims_diff["jaccard"], 0.0)
        self.assertLess(sims_diff["cosine"], 0.2)


class CryptographicSignatureTests(unittest.TestCase):
    def test_unsigned_pdf(self):
        pdf_path = os.path.join(SYN, "APP-001", "noc.pdf")
        res = ml_service.verify_pdf_signatures(pdf_path)
        self.assertIn(res["status"], ("unsigned", "none"))
        self.assertFalse(res["has_signature"])

    def test_raw_bytes_without_signature(self):
        raw = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        res = ml_service.verify_pdf_signatures(raw)
        self.assertEqual(res["status"], "unsigned")
        self.assertFalse(res["has_signature"])


class InfrastructureCVTests(unittest.TestCase):
    def test_quality_clean_image(self):
        # Create clean, sharp test image
        im = Image.new("RGB", (800, 800), color=(180, 180, 180))
        arr = np.array(im)
        # Add high-contrast text-like pattern
        arr[100:700:20, 100:700:20] = [0, 0, 0]
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, format="PNG")
        val = ml_service.assess_infrastructure_image(buf.getvalue())
        self.assertEqual(val["width"], 800)
        self.assertEqual(val["height"], 800)
        self.assertGreater(val["sharpness"], 45.0)
        self.assertIn("disclaimer", val)

    def test_quality_low_resolution_and_blur(self):
        # Create 200x200 uniform image (low res, low sharpness)
        im = Image.new("RGB", (200, 200), color=(100, 100, 100))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        val = ml_service.assess_infrastructure_image(buf.getvalue())
        self.assertFalse(val["usable"])
        self.assertTrue(any("resolution" in issue.lower() for issue in val["issues"]))
        self.assertTrue(any("blurry" in issue.lower() for issue in val["issues"]))

    def test_haversine_distance(self):
        # New Delhi to Mumbai ~ 1150 km
        d = ml_service.haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
        self.assertGreater(d, 1100.0)
        self.assertLess(d, 1200.0)

        # Same point -> 0 km
        self.assertEqual(ml_service.haversine_distance(28.6139, 77.2090, 28.6139, 77.2090), 0.0)


if __name__ == "__main__":
    unittest.main()
