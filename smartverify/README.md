# AICTE Vidya-Niriksha - prototype (synthetic data only)

AI-assisted application validation, document authentication and compliance checking. **Decision support only** - nothing here approves or rejects an application.

## Run
```bash
pip install -r requirements.txt          # + Tesseract binary:  apt install tesseract-ocr   (Windows: UB-Mannheim installer)
python app.py seed                       # creates the DB, encrypted demo uploads and demo users (password: demo123)
python app.py                            # http://127.0.0.1:5000
python -m unittest discover -s tests -t .   # 67 tests
python evaluate.py                       # writes data/eval_report.json (shown on the officer dashboard)
python app.py purge                      # retention: secure-delete documents of closed applications past the window
```
Set `SECRET_KEY` and `DOC_ENCRYPTION_KEY` in the environment for anything beyond a local demo (see SECURITY.md). Docker: `docker compose up --build`.
If you have an older `Vidya-Niriksha.db`, delete it first - the schema changed (re-run `python app.py seed`).

Demo logins: `inst1@demo.com` (clean app) · `inst2@demo.com` (problem app) · `inst3@demo.com` (scanned images) · `officer@demo.com` · `verifier@demo.com` · `admin@demo.com`.

## Layout
`app.py` routes + REST `/api/v1` · `services.py` business logic · `pipeline.py` end-to-end run · `core/` extractor, rules_engine, anomaly, mock_issuer, records, infra, security, storage ·
`core/rules.json` seed rules (live rules are versioned in the DB; edit them in Admin -> Rules) · `evaluate.py` + `tests/` · `FEATURES.md` PRD coverage matrix (read it for what is NOT done).

## Notes
* Regulatory `clause` fields are placeholders - a subject-matter expert must fill them from the Approval Process Handbook. One rule (`R-DEMO-COND`) is a switched-off example of conditional applicability.
* The mock issuer (`data/mock_registry.json`, reference prefixes `UNAVAIL*`, `FLAKY*`, `PENDING*`) is the only verification source; swap in real adapters only with authorization.
* The bundled synthetic PDFs were generated with a stand-in PDF library; run `python gen_synthetic.py` to regenerate them with your PyMuPDF.
