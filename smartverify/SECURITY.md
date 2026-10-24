# Vidya-Niriksha - security notes (prototype)

**Implemented:** role-based access with institution isolation; CSRF tokens on every state-changing request; salted password hashes (Werkzeug);
password policy for admin-created accounts; login throttling (5 failures / 10 min / IP+email); immediate session revocation (disable user / reset password);
upload checks (extension + magic bytes, size, page and pixel limits, encrypted-PDF rejection, EICAR + optional ClamAV scan); documents encrypted at rest (Fernet);
SSRF guard (`core/security.validate_outbound_url`, https-only, allow-listed hosts, private/loopback blocked) - the prototype never fetches QR/URL targets;
security headers; audit log of sign-ins, views, downloads, exports, uploads (incl. rejections), reviews, overrides, corrections, rule and user changes;
secrets from the environment; `python app.py purge` secure-deletes documents of closed applications past the retention window.

**You must do before any real use:** set `SECRET_KEY` and `DOC_ENCRYPTION_KEY` (keep the key in a secrets manager - losing it makes stored documents unreadable);
serve over HTTPS with `SESSION_COOKIE_SECURE=1`; replace the demo accounts (password `demo123`); use PostgreSQL; run a real malware scanner (ClamAV);
add a Content-Security-Policy (the UI currently loads Tailwind from a CDN, which prevents a strict one); move login throttling to shared storage if you run >1 worker.
Do not put real personal or institutional data in this prototype.

**Incident response (suggested):** 1) disable affected users (Admin -> Users -> Revoke access: kills live sessions); 2) rotate `SECRET_KEY` (invalidates all sessions);
3) export `Admin -> System audit` and per-application audit trails; 4) if the document key may be exposed, re-encrypt stored files with a new `DOC_ENCRYPTION_KEY`;
5) notify the data owner per your policy.
