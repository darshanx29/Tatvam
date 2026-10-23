# PRD coverage matrix

Legend: DONE = implemented and covered by tests · PARTIAL = works with stated limits · NOT DONE = deliberately left out (reason given).

| PRD | Status | Notes |
|---|---|---|
| FR-01 auth + RBAC | DONE | 4 roles, institution isolation, CSRF, throttling, session revocation, admin user management |
| FR-02/03 intake, category, checklist | DONE | draft -> submit, edit, version history, category list from rules, conditional checklists via `applies_when` |
| FR-04 upload/preview/storage | DONE | PDF/JPEG/PNG, magic-byte + size + page limits, malware screen, encrypted at rest, in-browser viewer |
| FR-05 OCR | DONE | text layer + Tesseract (PDF and images), OpenCV preprocessing, real word confidence, page + bounding box, officer correction (audited, survives re-runs) |
| FR-06 missing / incomplete / expired | DONE | incl. blank mandatory fields, missing identifiers, unreadable scans, unparseable dates (inconclusive, never a crash) |
| FR-07 cross-checks | DONE | application vs document, document vs document, vs authorized institutional record (mock `data/institution_records.json`) incl. programme + intake |
| FR-08 anomalies | PARTIAL | duplicates (hash; cross-institution reuse of file or certificate number), metadata, PDF structure (incremental saves, active content), QR host check, signature presence. **Visual-alteration (ELA) is experimental and OFF** (`ENABLE_ELA=1`): it could not separate tampered from clean test images, so it is not offered as a detector. **Signature validation reports "present, unvalidated"** unless pyHanko + trusted roots are installed. No ML anomaly model (needs real labelled data) |
| FR-09 source verification | DONE (mock) | PRD statuses, verification history table, bounded retries, manual verification by officers, outage != mismatch |
| FR-10 configurable rules | DONE | 14 rule types, versions + effective dates, conditions, admin screen, rule version on every finding |
| FR-11/12 results + officer review | DONE | findings with evidence, accept/dismiss/escalate/request evidence, observations, recommendation, close-in-prototype, institution responses + notifications, idempotent actions, override logging |
| FR-13 audit | DONE | sign-ins, views, downloads, exports, uploads (incl. rejected), reviews, overrides, corrections, rule/user/settings changes, rule versions per run |
| FR-14 export | DONE | server-side PDF, CSV, JSON, print view |
| FR-15 infrastructure CV | PARTIAL | advisory evidence-quality checks only (resolution, blur, exposure) -> inconclusive + inspection recommendation. Cannot establish measurements or safety, by design |
| FR-16 live AICTE portal | NOT DONE | needs authorization (PRD: future) |
| Dashboard KPIs | DONE | counts, % missing docs, processing median/p95, usable verification %, review time, status/severity charts, evaluation card |
| Compliance screen | DONE | compliant / deficient / inconclusive per rule with version, clause, evidence |
| Async + progress | PARTIAL | in-process thread pool with visible progress and failure handling; **no Celery/Redis** |
| Evaluation | PARTIAL | labelled synthetic set + metrics (OCR, findings P/R/FPR, anomalies, verification, timing). Only 4 apps / 16 documents, so results are not real-world accuracy |
| Security/privacy | PARTIAL | see SECURITY.md. No OIDC/OAuth, no S3/MinIO (storage class is swappable), no CSP (CDN Tailwind), throttling is per-process |
| Stack | CHANGED | kept Flask/Jinja (not FastAPI/Next.js), SQLite default with PostgreSQL via `DATABASE_URL`, Docker files provided (untested here) |
| Future items | NOT DONE | multilingual OCR (only the `OCR_LANGS` hook), layout-aware classifier (keyword scoring), workload prioritisation/SLA, recurring-deficiency analytics, e-mail notifications (in-app only) |
