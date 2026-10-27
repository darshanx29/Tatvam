# VidyaNiriksha — AICTE Compliance & Document Authentication Platform

VidyaNiriksha is an AI-assisted institutional application validation, document authentication, and regulatory compliance assistance platform designed for the AICTE approval process.

> **Decision Support Notice:** This system is an automated decision-support prototype. It does not replace statutory scrutiny, formal expert committee review, or competent administrative authority. All findings are evidence-linked preliminary indicators.

---

## 1. Quickstart Guide

### Prerequisites
- Python 3.11+ (tested on Python 3.11, 3.12, 3.14)
- Node.js 18+ & npm
- *(Optional)* Tesseract OCR binary (auto-detected on Windows `C:\Program Files\Tesseract-OCR\tesseract.exe` or Linux `apt install tesseract-ocr`). On systems without Tesseract installed, an embedded synthetic OCR fallback enables full test and review execution.

### Backend Setup (FastAPI)
```powershell
# From project root:
cd smartverify

# Activate virtual environment
..\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Seed demonstration database, cryptographic keys & synthetic test data
python backend/main.py seed

# Start the canonical FastAPI backend on port 5000
uvicorn backend.main:app --port 5000 --reload
```
API Health and Readiness endpoints:
- Health check: `http://127.0.0.1:5000/api/v1/health`
- Readiness probe: `http://127.0.0.1:5000/api/v1/ready`

### Frontend Setup (React + Vite)
```powershell
# In a separate terminal:
cd smartverify

# Start development dev server with hot-reload (proxied to backend :5000)
npm run dev
# Access UI at: http://localhost:5173

# Or build static production distribution (served by FastAPI at /)
npm run build
```

---

## 2. Automated Test Suite & Evaluation Benchmark

### Run Backend Unit & Integration Tests
```powershell
cd smartverify
python -m unittest discover -s backend/tests
```
Executes all 49 tests across:
- **Deterministic Rule Engine:** Mandatory documents, expiry date logic, date order, intake reconciliation, and institution ID cross-validation.
- **Evidence-Linked Anomaly Detection:** SHA-256 duplicate checking, perceptual hash (pHash) near-match, cross-institution duplicate alerts, PDF structure & metadata flags.
- **Verification Adapter Architecture:** Mock issuer simulation, timeout handling, retry boundaries, and manual verification tracking.
- **Security & RBAC:** Multi-tenant institution isolation, role enforcement (Institution, Scrutiny Officer, Verification Officer, Admin), session throttling (5-attempt brute-force lock), CSRF validation, and Fernet encryption-at-rest.
- **Cryptographic Audit Log:** SHA-256 hash chaining and tamper-evidence verification.

### Run Synthetic Evaluation Benchmark
```powershell
cd smartverify
python backend/evaluate.py
```
Computes field-level OCR accuracy, rule precision, anomaly precision/recall, and verification accuracy against hand-labelled ground truth. Results are saved to `backend/data/eval_report.json` and rendered in the Admin Telemetry dashboard.

---

## 3. Demo Personas & Credentials

All test accounts use password: `demo123`

| Role | Email | Purpose & Demo Workflow |
| :--- | :--- | :--- |
| **Institution Admin (Clean)** | `inst1@demo.com` | `SV-TEST-001` (Clean application, all required documents present and valid, passes preliminary checks). |
| **Institution Admin (Deficient)** | `inst2@demo.com` | `SV-TEST-002` (Problem application: expired NAAC cert, wrong institution ID on NOC, missing affidavit, cross-doc mismatch). |
| **Institution Admin (Scans)** | `inst3@demo.com` | `SV-TEST-003` / `SV-TEST-004` (Scanned image application, blurred lab photo flagged for physical inspection). |
| **Scrutiny Officer** | `officer@demo.com` | Scrutiny review, OCR field correction with justification, evidence request, and formal recommendations. |
| **Verification Officer** | `verifier@demo.com` | Source verification adapter execution, retry handling, and manual verification recording. |
| **System Administrator** | `admin@demo.com` | User management, rule versioning, SSRF allow-lists, and cryptographic audit log verification. |

---

## 4. Key Architecture & Features

### A. Document Intelligence & OCR Pipeline
- Text extraction from digital PDFs via PyMuPDF (`fitz`).
- Preprocessing (illumination flattening, projection-profile deskewing, resolution upscaling) before OCR.
- Field extraction with token-level bounding boxes and confidence scores (`pw`, `ph`, `bbox`).
- Human-in-the-loop OCR correction modal preserving original values and audit trail.

### B. Unified Verification Adapter Architecture (`backend/core/adapters.py`)
- Standardized verification statuses:
  - `VERIFIED`: Confirmed by authoritative source.
  - `MISMATCH_DETECTED`: Extracted field conflicts with issuer record.
  - `EXPIRED`: Document valid-until date has elapsed in issuer records.
  - `PENDING`: Async verification in progress.
  - `SOURCE_UNAVAILABLE`: Network timeout or issuer downtime (clearly distinct from failure).
  - `MANUAL_REVIEW_REQUIRED`: Unresolved reference routed to officer.
  - `INCONCLUSIVE`: Ambiguous evidence requiring physical inspection.

### C. Tamper-Evident Audit Logging
- Every administrative action, document upload, validation run, review decision, and rule version change is cryptographically hash-chained (`prev_hash` + SHA-256 payload).
- Dedicated admin verification endpoint (`/api/v1/admin/audit/verify`) dynamically audits the integrity of the chain.

### D. Document Security & Storage
- Upload sniffing (magic bytes, MIME type, file extension, max page limit, max file size).
- Antivirus signature screening (EICAR) and ClamAV hook.
- Server-side encrypted storage using Fernet (`backend/core/storage.py`) — documents are encrypted at rest and never accessible from public static URLs.

---

## 5. Docker Deployment

```bash
cd smartverify
docker compose up --build
```
Builds the containerized environment on port 5000 with volume persistence for encrypted uploads and database storage.
