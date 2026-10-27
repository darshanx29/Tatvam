"""AICTE SmartVerify - FastAPI application.
Run:
    python backend/main.py seed      # to seed test database
    uvicorn backend.main:app --port 5000 --reload
"""
import io
import json
import os
import secrets
import shutil
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import reporting
import services as S
from core import records, rules_engine, security
from models import (
    ADMIN, INSTITUTION, OFFICERS, OPEN_STATES, ROLE_LABEL, SCRUTINY, VERIFIER,
    Application, ApplicationVersion, AuditEvent, Document, ExtractedField,
    Finding, Notification, ProcessingRun, ReviewAction, RuleVersion, Setting,
    User, VerificationRecord, db
)

BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE, "..", "frontend", "dist"))

# In-memory login throttling: (ip, email) -> [timestamps]
_fails = {}
LOGIN_MAX_FAILS = 5
LOGIN_WINDOW_S = 600

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set - using a temporary random key.", file=sys.stderr)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_all()
    S.seed_rules()
    yield

app = FastAPI(
    title="AICTE SmartVerify API",
    description="Automated Institutional Approval Verification Engine & Decision Support System",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------ Middleware
@app.middleware("http")
async def db_session_and_security_headers_middleware(request: Request, call_next):
    # Ensure CSRF token exists on session
    if "csrf" not in request.session:
        request.session["csrf"] = security.new_csrf()

    try:
        response = await call_next(request)
    finally:
        db.session.remove()

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    if "uid" in request.session:
        response.headers["Cache-Control"] = "no-store"

    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="smartverify_session",
    max_age=8 * 3600,
    same_site="lax",
    https_only=(os.environ.get("SESSION_COOKIE_SECURE") == "1")
)


# ------------------------------------------------------------------ Auth & Access Helpers
def get_current_user(request: Request) -> Optional[User]:
    uid = request.session.get("uid")
    if not uid:
        return None
    user = db.session.get(User, uid)
    if not user or not user.active or request.session.get("epoch") != user.session_epoch:
        request.session.clear()
        return None
    S.set_current_actor(user.email)
    return user


def require_auth(request: Request) -> User:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    return user


def require_role(*roles):
    def dependency(request: Request) -> User:
        user = require_auth(request)
        if roles and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user
    return dependency


def get_app_or_403(app_id: str, user: User) -> Application:
    a = db.session.get(Application, app_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if user.role == INSTITUTION and user.institution_id != a.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Institutions can only view their own records")
    if user.role != INSTITUTION and a.status == "Draft":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft applications are private to the institution")
    return a


def get_doc_or_403(did: int, user: User):
    d = db.session.get(Document, did)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    a = get_app_or_403(d.app_id, user)
    return d, a


def can_manage(a: Application, u: User) -> bool:
    return u.role == INSTITUTION and u.institution_id == a.institution_id


def verify_csrf(request: Request, x_csrf_token: Optional[str] = Header(None)):
    session_csrf = request.session.get("csrf")
    if not security.csrf_ok(session_csrf, x_csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSRF token missing or invalid")


# ------------------------------------------------------------------ Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    msg = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": msg, "detail": detail, "status_code": exc.status_code},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("uvicorn.error").error(f"Unhandled error processing {request.url.path}: {type(exc).__name__}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An internal server error occurred.", "detail": "Internal error"},
    )


# ============================================================================ REST API /api/v1
# ------------------------------------------------------------------ Health & Readiness
@app.get("/api/v1/health")
def api_health():
    return {
        "status": "ok",
        "service": "AICTE SmartVerify API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/v1/ready")
def api_ready():
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    storage_ok = os.path.isdir(S.UPLOADS_DIR) or os.path.exists(os.path.dirname(S.UPLOADS_DIR))

    if not db_ok or not storage_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": db_ok, "storage": storage_ok}
        )

    return {
        "status": "ready",
        "database": "connected",
        "storage": "accessible",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

# ------------------------------------------------------------------ Auth
@app.post("/api/v1/login")
async def api_login(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = (client_ip, email)
    now = time.time()

    recent = [t for t in _fails.get(key, []) if now - t < LOGIN_WINDOW_S]
    if len(recent) >= LOGIN_MAX_FAILS:
        S.audit("SYSTEM", "login_throttled", email)
        db.session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed attempts. Try again in a few minutes.")

    u = User.query.filter_by(email=email).first()
    if u and u.active and check_password_hash(u.password_hash, pw):
        _fails.pop(key, None)
        csrf = request.session.get("csrf") or security.new_csrf()
        request.session.clear()
        request.session["uid"] = u.id
        request.session["email"] = u.email
        request.session["epoch"] = u.session_epoch
        request.session["csrf"] = csrf

        S.audit("SYSTEM", "login_success", u.email, actor=u.email)
        db.session.commit()

        return {
            "user": {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "role_label": ROLE_LABEL.get(u.role, u.role),
                "institution_id": u.institution_id
            },
            "csrf_token": csrf
        }

    _fails[key] = recent + [now]
    S.audit("SYSTEM", "login_failed", email, actor=email)
    db.session.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


@app.api_route("/api/v1/logout", methods=["GET", "POST"])
def api_logout(request: Request):
    user = get_current_user(request)
    if user:
        S.audit("SYSTEM", "logout", "", actor=user.email)
        db.session.commit()
    request.session.clear()
    return {"ok": True}


@app.get("/api/v1/me")
def api_me(request: Request):
    user = get_current_user(request)
    csrf = request.session.get("csrf") or security.new_csrf()
    request.session["csrf"] = csrf
    if not user:
        return {"authenticated": False, "csrf_token": csrf}
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "role_label": ROLE_LABEL.get(user.role, user.role),
            "institution_id": user.institution_id
        },
        "csrf_token": csrf
    }


# ------------------------------------------------------------------ Dashboard
@app.get("/api/v1/dashboard")
def api_dashboard(
    request: Request,
    q: Optional[str] = "",
    status: Optional[str] = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    user: User = Depends(require_auth)
):
    query = Application.query
    if user.role == INSTITUTION:
        query = query.filter_by(institution_id=user.institution_id)
    else:
        query = query.filter(Application.status != "Draft")

    allapps = query.order_by(Application.created_at.desc()).all()
    text = (q or "").strip().lower()
    st = (status or "").strip()

    filtered = [
        a for a in allapps
        if (not text or text in a.id.lower() or text in (a.institution_id or "").lower())
        and (not st or a.status == st)
    ]

    pages = max((len(filtered) + per_page - 1) // per_page, 1)
    ids = [a.id for a in filtered]
    counts = {}
    if ids:
        for f in Finding.query.filter(Finding.app_id.in_(ids), Finding.state.in_(OPEN_STATES)):
            counts[f.app_id] = counts.get(f.app_id, 0) + 1

    alerts = AuditEvent.query.filter(AuditEvent.app_id.in_([a.id for a in allapps])).order_by(
        AuditEvent.ts.desc(), AuditEvent.id.desc()
    ).limit(8).all() if allapps else []

    high = Finding.query.filter(
        Finding.app_id.in_([a.id for a in allapps]),
        Finding.state == "open",
        Finding.severity == "high"
    ).order_by(Finding.id.desc()).limit(5).all() if allapps and user.role != INSTITUTION else []

    notes = Notification.query.filter_by(
        institution_id=user.institution_id, read=False
    ).order_by(Notification.id.desc()).all() if user.role == INSTITUTION else []

    return {
        "kpi": S.kpis(allapps),
        "evaluation_report": S.evaluation_report(),
        "alerts": [
            {"id": e.id, "app_id": e.app_id, "event": e.event, "actor": e.actor, "detail": e.detail, "ts": e.ts.strftime("%d-%m-%Y %H:%M")}
            for e in alerts
        ],
        "high": [
            {"id": h.id, "app_id": h.app_id, "title": h.title, "source": h.source, "severity": h.severity}
            for h in high
        ],
        "notes": [
            {"id": n.id, "app_id": n.app_id, "message": n.message, "created_at": n.created_at.strftime("%d-%m-%Y %H:%M")}
            for n in notes
        ],
        "apps": [
            {
                **a.as_dict(),
                "created_at": a.created_at.strftime("%d-%m-%Y %H:%M") if a.created_at else None,
                "open_count": counts.get(a.id, 0)
            }
            for a in filtered[(page - 1) * per_page: page * per_page]
        ],
        "total": len(filtered),
        "page": page,
        "pages": pages,
        "statuses": sorted({a.status for a in allapps})
    }


@app.post("/api/v1/notifications/read")
def api_notifications_read(user: User = Depends(require_role(INSTITUTION))):
    Notification.query.filter_by(institution_id=user.institution_id).update({"read": True})
    db.session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Applications
@app.post("/api/v1/applications", status_code=status.HTTP_201_CREATED)
async def api_create_application(
    request: Request,
    user: User = Depends(require_role(INSTITUTION))
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        data = dict(form)
        files = form.getlist("files")
    else:
        data = await request.json()
        files = []

    a = S.create_application(user, data)
    saved, rej = S.store_uploads(a, files, actor=user.email) if files else (0, [])
    action = data.get("action", "draft")

    if action == "submit":
        miss = S.missing_for_submit(a)
        if miss:
            db.session.commit()
            return JSONResponse(
                status_code=400,
                content={"application": a.as_dict(), "error": "Saved as draft. Still needed before submission: " + ", ".join(miss)}
            )
        a.status, a.submitted_at = "Submitted", datetime.now()
        S.snapshot(a, "submitted", actor=user.email)
        S.audit(a.id, "application_submitted", "", actor=user.email)
        db.session.commit()
        S.queue_validation(a)
        return {"application": a.as_dict(), "saved": saved, "message": "Application submitted; preliminary checks are running."}

    db.session.commit()
    return {"application": a.as_dict(), "saved": saved, "message": "Draft saved."}


@app.get("/api/v1/applications")
def api_list_applications(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    user: User = Depends(require_auth)
):
    query = Application.query
    if user.role == INSTITUTION:
        query = query.filter_by(institution_id=user.institution_id)
    else:
        query = query.filter(Application.status != "Draft")

    rows = query.order_by(Application.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {"page": page, "items": [a.as_dict() for a in rows]}


@app.get("/api/v1/applications/{app_id}")
def api_get_application(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    return a.as_dict()


@app.get("/api/v1/applications/{app_id}/full")
def api_application_full(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    officer = user.role != INSTITUTION

    docs = Document.query.filter_by(app_id=a.id).order_by(Document.name).all()
    have = {d.doc_type for d in docs}
    checklist = [
        {"doc_type": t, "title": title, "rule_id": rid, "present": t in have}
        for t, title, rid in S.required_docs(a)
    ]
    findings = Finding.query.filter_by(app_id=a.id).order_by(Finding.id).all()
    acts = ReviewAction.query.filter_by(app_id=a.id).order_by(ReviewAction.ts).all()

    by_f = {}
    for x in acts:
        if x.finding_id:
            by_f.setdefault(x.finding_id, []).append({
                "id": x.id, "actor": x.actor, "action": x.action, "reason": x.reason,
                "ts": x.ts.strftime("%d-%m-%Y %H:%M")
            })

    run = ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first()
    versions = ApplicationVersion.query.filter_by(app_id=a.id).order_by(ApplicationVersion.id.desc()).all()
    notes = [x for x in acts if x.action in ("observation", "recommendation", "close")]

    doc_list = []
    for d in docs:
        low_conf = sum(1 for f in d.fields if (f.confidence or 0) < 0.8)
        cor_count = sum(1 for f in d.fields if f.corrected_by)
        doc_list.append({
            "id": d.id, "name": d.name, "doc_type": d.doc_type, "ocr_method": d.ocr_method,
            "class_conf": d.class_conf, "mean_conf": d.mean_conf, "sha": d.sha, "size": d.size,
            "signature": d.signature or "none", "fields_count": len(d.fields),
            "low_conf_count": low_conf, "corrected_count": cor_count,
            "quality": d.quality
        })

    return {
        "application": {
            **a.as_dict(),
            "created_at": a.created_at.strftime("%d-%m-%Y %H:%M") if a.created_at else None,
            "submitted_at": a.submitted_at.strftime("%d-%m-%Y %H:%M") if a.submitted_at else None,
            "recommendation_note": a.recommendation_note,
            "closed_at": a.closed_at.strftime("%d-%m-%Y %H:%M") if a.closed_at else None
        },
        "mine": can_manage(a, user),
        "docs": doc_list,
        "checklist": checklist,
        "findings": [
            {
                **f.as_dict(officer),
                "reviews": by_f.get(f.id, [])
            }
            for f in findings
        ],
        "verifications": S.effective_verifications(a),
        "run": ({"status": run.status, "progress": run.progress, "message": run.message} if run else None),
        "versions": [
            {
                "version": v.version, "actor": v.actor, "reason": v.reason,
                "ts": v.ts.strftime("%d-%m-%Y %H:%M"), "snapshot": v.snapshot_json
            }
            for v in versions
        ],
        "notes": [
            {
                "id": n.id, "actor": n.actor, "action": n.action, "reason": n.reason,
                "ts": n.ts.strftime("%d-%m-%Y %H:%M")
            }
            for n in notes
        ],
        "categories": S.categories(),
        "recommendation_options": S.RECOMMENDATIONS,
        "infra_docs": [
            {"id": d.id, "name": d.name, "quality": d.quality}
            for d in docs if d.quality
        ]
    }


@app.post("/api/v1/applications/{app_id}/edit")
async def api_edit_application(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(INSTITUTION))
):
    a = get_app_or_403(app_id, user)
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        data = dict(form)
        files = form.getlist("files")
    else:
        data = await request.json()
        files = []

    ok, msg = S.edit_application(a, data, actor=user.email)
    saved, rej = S.store_uploads(a, files, actor=user.email) if files else (0, [])
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg, "saved": saved, "rejected": rej}


@app.post("/api/v1/applications/{app_id}/submit")
def api_submit_application(app_id: str, user: User = Depends(require_role(INSTITUTION))):
    a = get_app_or_403(app_id, user)
    if a.status != "Draft":
        raise HTTPException(status_code=400, detail="Already submitted.")
    miss = S.missing_for_submit(a)
    if miss:
        raise HTTPException(status_code=400, detail="Cannot submit yet. Missing: " + ", ".join(miss))

    a.status, a.submitted_at = "Submitted", datetime.now()
    S.snapshot(a, "submitted", actor=user.email)
    S.audit(a.id, "application_submitted", "", actor=user.email)
    db.session.commit()
    S.queue_validation(a)
    return {"ok": True, "message": "Application submitted; preliminary checks are running."}


@app.post("/api/v1/applications/{app_id}/documents")
async def api_upload_documents(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(INSTITUTION))
):
    a = get_app_or_403(app_id, user)
    form = await request.form()
    files = form.getlist("files")
    saved, rej = S.store_uploads(a, files, actor=user.email)

    if a.status == "Closed in prototype":
        a.status, a.closed_at = "Submitted", None
    db.session.commit()

    if saved and a.status != "Draft":
        S.queue_validation(a)

    if not saved and rej:
        raise HTTPException(status_code=400, detail="; ".join(rej))

    return {"saved": saved, "rejected": rej}


@app.get("/api/v1/applications/{app_id}/checklist")
def api_checklist(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    have = {d.doc_type for d in Document.query.filter_by(app_id=a.id)}
    return {
        "items": [
            {"doc_type": t, "title": title, "rule_id": rid, "present": t in have}
            for t, title, rid in S.required_docs(a)
        ]
    }


@app.post("/api/v1/applications/{app_id}/validate", status_code=status.HTTP_202_ACCEPTED)
def api_validate_application(
    app_id: str,
    user: User = Depends(require_role(INSTITUTION, SCRUTINY, VERIFIER, ADMIN))
):
    a = get_app_or_403(app_id, user)
    if a.status == "Draft":
        raise HTTPException(status_code=409, detail="Submit the draft first.")
    run, started = S.queue_validation(a)
    return {"run_id": run.id, "started": started, "status": run.status}


@app.get("/api/v1/applications/{app_id}/status")
def api_application_status(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    run = ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first()
    return {
        "application_status": a.status,
        "run": ({"status": run.status, "progress": run.progress, "message": run.message} if run else None)
    }


@app.get("/api/v1/applications/{app_id}/findings")
def api_application_findings(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    officer = user.role != INSTITUTION
    rows = Finding.query.filter(Finding.app_id == a.id, Finding.state != "resolved").order_by(Finding.id).all()
    return {"items": [f.as_dict(officer) for f in rows]}


# ------------------------------------------------------------------ Documents & Fields
@app.get("/api/v1/documents/{did}")
def api_doc_view(did: int, user: User = Depends(require_auth)):
    d, a = get_doc_or_403(did, user)
    try:
        data = S.storage().read(a.id, d.name)
    except Exception:
        data = b""
    npages = 1
    if d.name.lower().endswith(".pdf") and data:
        try:
            import pymupdf
            npages = max(pymupdf.open(stream=data, filetype="pdf").page_count, 1)
        except Exception:
            pass

    ver = next((v for v in S.effective_verifications(a) if v["document"] == d.name), None)
    flags = Finding.query.filter(
        Finding.app_id == a.id,
        Finding.kind == "anomaly",
        Finding.state != "resolved",
        Finding.source.contains(d.name)
    ).all()
    qr = json.loads(d.qr_json or "[]")
    fields = [
        {
            "id": f.id, "name": f.name, "value": f.value, "confidence": f.confidence,
            "page": f.page, "bbox": f.bbox, "page_w": f.page_w, "page_h": f.page_h,
            "original_value": f.original_value, "corrected_by": f.corrected_by
        }
        for f in d.fields
    ]

    return {
        "document": {
            "id": d.id, "name": d.name, "doc_type": d.doc_type, "ocr_method": d.ocr_method,
            "class_conf": d.class_conf, "mean_conf": d.mean_conf, "sha": d.sha, "size": d.size,
            "signature": d.signature or "none", "npages": npages
        },
        "fields": fields,
        "verification": ver,
        "flags": [{"title": f.title, "observed": f.observed, "reason": f.reason} for f in flags],
        "qr": qr,
        "mine": can_manage(a, user)
    }


@app.post("/api/v1/fields/{fid}/correct")
async def api_correct_field(
    fid: int,
    request: Request,
    user: User = Depends(require_role(SCRUTINY, VERIFIER))
):
    f = db.session.get(ExtractedField, fid)
    if not f:
        raise HTTPException(status_code=404, detail="Field not found")
    a = get_app_or_403(f.document.app_id, user)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    ok, msg = S.correct_field(a, f, body.get("value", ""), body.get("reason", ""), user.email)
    db.session.commit()
    if ok:
        S.queue_validation(a)
    else:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.post("/api/v1/findings/{fid}/review")
async def api_review_finding(
    fid: int,
    request: Request,
    user: User = Depends(require_role(SCRUTINY, VERIFIER))
):
    f = db.session.get(Finding, fid)
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    get_app_or_403(f.app_id, user)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    token = body.get("token") or uuid.uuid4().hex
    ok, msg = S.apply_review(f, user.email, body.get("action"), body.get("reason", ""), token)
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg, "state": f.state}


@app.post("/api/v1/findings/{fid}/respond")
async def api_respond_finding(
    fid: int,
    request: Request,
    user: User = Depends(require_role(INSTITUTION))
):
    f = db.session.get(Finding, fid)
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    a = get_app_or_403(f.app_id, user)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    token = body.get("token") or uuid.uuid4().hex
    text = body.get("text", "")
    ok, msg = S.add_note(a, user.email, "institution_response", f"[{f.rule_id} / {f.source}] " + text, token)
    if ok:
        last = ReviewAction.query.filter_by(app_id=a.id, action="institution_response", finding_id=None).order_by(ReviewAction.id.desc()).first()
        if last:
            last.finding_id = f.id
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": "Response recorded for the officer."}


@app.post("/api/v1/applications/{app_id}/observation")
async def api_observation(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(SCRUTINY, VERIFIER))
):
    a = get_app_or_403(app_id, user)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    token = body.get("token") or uuid.uuid4().hex
    ok, msg = S.add_note(a, user.email, "observation", body.get("text", ""), token)
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.post("/api/v1/applications/{app_id}/recommendation")
async def api_recommendation(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(SCRUTINY, VERIFIER))
):
    a = get_app_or_403(app_id, user)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    token = body.get("token") or uuid.uuid4().hex
    ok, msg = S.set_recommendation(a, user.email, body.get("choice"), body.get("note", ""), token)
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.post("/api/v1/applications/{app_id}/close")
def api_close_app(app_id: str, user: User = Depends(require_role(SCRUTINY, VERIFIER))):
    a = get_app_or_403(app_id, user)
    ok, msg = S.close_in_prototype(a, user.email)
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.post("/api/v1/applications/{app_id}/reverify")
async def api_reverify(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(SCRUTINY, VERIFIER))
):
    a = get_app_or_403(app_id, user)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    ok, msg = S.reverify(a, body.get("document", ""), actor=user.email)
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.post("/api/v1/applications/{app_id}/manual-verify")
async def api_manual_verify(
    app_id: str,
    request: Request,
    user: User = Depends(require_role(VERIFIER, SCRUTINY))
):
    a = get_app_or_403(app_id, user)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    ok, msg = S.record_manual_verification(
        a, body.get("document", ""), body.get("outcome", ""),
        body.get("reference", ""), body.get("note", ""), user.email
    )
    db.session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": ok, "message": msg}


@app.get("/api/v1/applications/{app_id}/compliance")
def api_compliance(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    rep = a.report
    res = rep.get("assessment", [])
    order = {"FAIL": 0, "INCONCLUSIVE": 1, "PASS": 2, "NOT_APPLICABLE": 3}
    res = sorted(res, key=lambda x: (order.get(x["status"], 9), x["rule_id"]))
    summary = {
        "compliant": sum(x["status"] == "PASS" for x in res),
        "deficient": sum(x["status"] == "FAIL" for x in res),
        "inconclusive": sum(x["status"] == "INCONCLUSIVE" for x in res)
    }
    refer = [x for x in res if x["status"] == "INCONCLUSIVE" and x.get("rule_type") == "infra_quality"]
    return {"res": res, "summary": summary, "refer": refer, "rules_used": rep.get("rules_used", [])}


@app.get("/api/v1/applications/{app_id}/audit")
def api_application_audit(app_id: str, user: User = Depends(require_auth)):
    a = get_app_or_403(app_id, user)
    ev = AuditEvent.query.filter_by(app_id=a.id).order_by(AuditEvent.id.desc()).all()
    return {
        "items": [
            {"ts": e.ts.strftime("%d-%m-%Y %H:%M:%S"), "actor": e.actor, "event": e.event, "detail": e.detail}
            for e in ev
        ]
    }


# ------------------------------------------------------------------ Rules & Admin
@app.get("/api/v1/rules")
def api_rules(user: User = Depends(require_role(SCRUTINY, VERIFIER, ADMIN))):
    today = datetime.now()
    in_force = {r["id"] for r in rules_engine.select_versions(S.all_rule_defs(), today)}
    latest = S.latest_rule_versions()
    return {
        "items": [
            {**rv.definition, "in_force": rv.rule_id in in_force}
            for rv in latest.values()
        ],
        "types": rules_engine.TYPES
    }


@app.post("/api/v1/admin/rules")
async def api_admin_rule_save(
    request: Request,
    user: User = Depends(require_role(ADMIN))
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    defn = body.get("definition")
    rule_id = body.get("rule_id")
    note = body.get("note", "")

    if not defn or not isinstance(defn, dict):
        raise HTTPException(status_code=400, detail="Valid rule definition JSON required")
    if rule_id and defn.get("id") != rule_id:
        raise HTTPException(status_code=400, detail="Rule id cannot be changed; create a new rule instead.")
    elif not rule_id and S.latest_rule_versions().get(defn.get("id")):
        raise HTTPException(status_code=400, detail="That rule id already exists - edit the existing rule.")

    ok, msg = S.save_rule_version(defn, user.email, note)
    if ok:
        db.session.commit()
        return {"ok": True, "version": msg}
    raise HTTPException(status_code=400, detail=msg)


@app.get("/api/v1/admin/users")
def api_admin_users_get(user: User = Depends(require_role(ADMIN))):
    users = User.query.order_by(User.id).all()
    return {
        "users": [
            {
                "id": u.id, "email": u.email, "name": u.name, "role": u.role,
                "role_label": ROLE_LABEL.get(u.role, u.role), "institution_id": u.institution_id, "active": u.active
            }
            for u in users
        ],
        "roles": ROLE_LABEL
    }


@app.post("/api/v1/admin/users", status_code=status.HTTP_201_CREATED)
async def api_admin_users_create(
    request: Request,
    user: User = Depends(require_role(ADMIN))
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    email = (data.get("email") or "").strip().lower()
    role = data.get("role")
    pw = data.get("password") or ""
    prob = security.password_problem(pw)

    if not email or role not in ROLE_LABEL:
        raise HTTPException(status_code=400, detail="Email and valid role are required.")
    elif prob:
        raise HTTPException(status_code=400, detail=prob)
    elif User.query.filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="A user with that email already exists.")
    elif role == INSTITUTION and not (data.get("institution_id") or "").strip():
        raise HTTPException(status_code=400, detail="Institution users need an institution ID.")

    new_user = User(
        email=email,
        name=data.get("name") or email,
        role=role,
        password_hash=generate_password_hash(pw),
        institution_id=(data.get("institution_id") or "").strip() or None
    )
    db.session.add(new_user)
    S.audit("SYSTEM", "user_created", f"{email} ({role})", actor=user.email)
    db.session.commit()

    return {
        "ok": True,
        "user": {
            "id": new_user.id, "email": new_user.email, "name": new_user.name,
            "role": new_user.role, "institution_id": new_user.institution_id, "active": new_user.active
        }
    }


@app.post("/api/v1/admin/users/{uid}/toggle")
def api_admin_user_toggle(uid: int, user: User = Depends(require_role(ADMIN))):
    t = db.session.get(User, uid)
    if not t:
        raise HTTPException(status_code=404, detail="User not found")
    if t.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    t.active = not t.active
    t.session_epoch += 1
    S.audit("SYSTEM", "user_enabled" if t.active else "access_revoked", t.email, actor=user.email)
    db.session.commit()
    return {"ok": True, "active": t.active}


@app.post("/api/v1/admin/users/{uid}/password")
async def api_admin_user_password(
    uid: int,
    request: Request,
    user: User = Depends(require_role(ADMIN))
):
    t = db.session.get(User, uid)
    if not t:
        raise HTTPException(status_code=404, detail="User not found")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    pw = body.get("password", "")
    prob = security.password_problem(pw)
    if prob:
        raise HTTPException(status_code=400, detail=prob)

    t.password_hash = generate_password_hash(pw)
    t.session_epoch += 1
    S.audit("SYSTEM", "password_reset", t.email, actor=user.email)
    db.session.commit()
    return {"ok": True, "message": "Password reset successfully."}


@app.get("/api/v1/admin/settings")
def api_admin_settings_get(user: User = Depends(require_role(ADMIN))):
    vals = {k: S.get_setting(k) for k in S.SETTING_DEFAULTS}
    runs = ProcessingRun.query.order_by(ProcessingRun.id.desc()).limit(10).all()
    return {
        "settings": vals,
        "evaluation": S.evaluation_report(),
        "runs": [
            {
                "app_id": r.app_id, "status": r.status, "duration_s": r.duration_s,
                "started": r.started.strftime("%d-%m %H:%M") if r.started else None
            }
            for r in runs
        ],
        "adapter": "MOCK-ISSUER-REGISTRY (data/mock_registry.json)"
    }


@app.post("/api/v1/admin/settings")
async def api_admin_settings_save(
    request: Request,
    user: User = Depends(require_role(ADMIN))
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    for k in S.SETTING_DEFAULTS:
        if k in data:
            S.set_setting(k, str(data[k]).strip())

    S.audit("SYSTEM", "settings_changed", ", ".join(S.SETTING_DEFAULTS), actor=user.email)
    db.session.commit()
    return {"ok": True}


@app.get("/api/v1/admin/audit")
def api_admin_audit(user: User = Depends(require_role(ADMIN))):
    ev = AuditEvent.query.filter(
        (AuditEvent.app_id == "SYSTEM") | (AuditEvent.app_id == None)  # noqa: E711
    ).order_by(AuditEvent.id.desc()).limit(300).all()
    return {
        "items": [
            {"id": e.id, "actor": e.actor, "event": e.event, "detail": e.detail, "ts": e.ts.strftime("%d-%m-%Y %H:%M:%S")}
            for e in ev
        ]
    }


@app.get("/api/v1/admin/audit/verify")
def api_admin_audit_verify(user: User = Depends(require_role(ADMIN))):
    ok, count, msg = S.verify_audit_chain()
    return {
        "ok": ok,
        "verified_events": count if ok else None,
        "broken_event_id": None if ok else count,
        "message": msg
    }


# ============================================================================ Document Media & Reports
def _fetch_doc_data(a, d):
    try:
        return S.storage().read(a.id, d.name)
    except Exception:
        pass
    # Fallback to synthetic templates if file not yet encrypted in storage
    for syn in ("APP-001", "APP-002", "APP-003", "APP-004"):
        syn_path = os.path.join(BASE, "data", "synthetic", syn, d.name)
        if os.path.isfile(syn_path):
            with open(syn_path, "rb") as fh:
                data = fh.read()
            try:
                S.storage().save(a.id, d.name, data)
            except Exception:
                pass
            return data
    return None


@app.get("/documents/{did}/file")
def doc_file(
    did: int,
    dl: Optional[str] = "0",
    user: User = Depends(require_auth)
):
    d, a = get_doc_or_403(did, user)
    data = _fetch_doc_data(a, d)
    if data is None:
        raise HTTPException(status_code=404, detail="File content not found on disk")
    S.audit(a.id, "document_downloaded", d.name, actor=user.email)
    db.session.commit()

    ext = d.name.rsplit(".", 1)[-1].lower() if "." in d.name else ""
    mime_map = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
    mt = mime_map.get(ext, "application/octet-stream")

    headers = {}
    if dl == "1":
        headers["Content-Disposition"] = f'attachment; filename="{d.name}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{d.name}"'

    return StreamingResponse(io.BytesIO(data), media_type=mt, headers=headers)


@app.get("/documents/{did}/page/{n}.png")
def doc_page(
    did: int,
    n: int,
    user: User = Depends(require_auth)
):
    from PIL import Image
    d, a = get_doc_or_403(did, user)
    data = _fetch_doc_data(a, d)
    if data is None:
        # Graceful placeholder preview when physical file is missing from disk
        from PIL import ImageDraw
        img = Image.new("RGB", (1000, 1400), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)
        draw.rectangle([40, 40, 960, 1360], outline=(203, 213, 225), width=2)
        draw.text((80, 150), f"Document: {d.name}", fill=(30, 41, 59))
        draw.text((80, 200), f"Application ID: {a.id}", fill=(100, 116, 139))
        draw.text((80, 250), f"Page {n} Preview", fill=(100, 116, 139))
        draw.text((80, 340), "Notice: Original encrypted document file is not present in storage.", fill=(185, 28, 28))
        draw.text((80, 380), "Please re-upload this document in the application to restore preview.", fill=(100, 116, 139))
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return StreamingResponse(out, media_type="image/png")

    if d.name.lower().endswith(".pdf"):
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="pdf")
        page_idx = max(min(n, doc.page_count), 1) - 1
        pix = doc[page_idx].get_pixmap(dpi=100)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    else:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.width > 1600:
            img = img.resize((1600, int(img.height * 1600 / img.width)))

    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return StreamingResponse(out, media_type="image/png")


@app.get("/applications/{app_id}/report.{fmt}")
def report_export(
    app_id: str,
    fmt: str,
    user: User = Depends(require_auth)
):
    a = get_app_or_403(app_id, user)
    officer = user.role != INSTITUTION

    findings = Finding.query.filter(Finding.app_id == a.id, Finding.state != "resolved").order_by(Finding.id).all()
    acts = ReviewAction.query.filter_by(app_id=a.id).order_by(ReviewAction.ts).all()
    verifs = S.effective_verifications(a)
    assess = a.report.get("assessment", [])

    d = reporting.data(a, findings, acts, verifs, assess, officer)
    S.audit(a.id, "report_exported", fmt, actor=user.email)
    db.session.commit()

    if fmt == "json":
        return Response(
            content=reporting.to_json(d),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{a.id}-report.json"'}
        )
    elif fmt == "csv":
        return Response(
            content=reporting.to_csv(d),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{a.id}-report.csv"'}
        )
    elif fmt == "pdf":
        return Response(
            content=reporting.to_pdf(d),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{a.id}-report.pdf"'}
        )
    raise HTTPException(status_code=404, detail="Format not supported. Use json, csv, or pdf.")


# ============================================================================ Frontend Static Files & SPA
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


@app.get("/react/{full_path:path}")
@app.get("/react")
@app.get("/app/{full_path:path}")
@app.get("/app")
@app.get("/")
def serve_spa(full_path: Optional[str] = None):
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_file):
        return Response(
            content="React app has not been built yet. Run 'npm run build' in the frontend directory.",
            media_type="text/plain",
            status_code=404
        )
    if full_path:
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
    return FileResponse(index_file)


# ============================================================================ Seed & CLI
def seed():
    db.drop_all()
    db.create_all()
    uploads_dir = S.UPLOADS_DIR
    shutil.rmtree(uploads_dir, ignore_errors=True)
    os.makedirs(uploads_dir, exist_ok=True)
    S.seed_rules()

    if not os.path.isdir(os.path.join(BASE, "data", "synthetic", "APP-001")):
        import gen_synthetic
        gen_synthetic.app001()
        gen_synthetic.app002()
        gen_synthetic.app003()
        gen_synthetic.app004()
        json.dump(gen_synthetic.REG, open(os.path.join(BASE, "data", "mock_registry.json"), "w"), indent=2)

    pw = generate_password_hash("demo123")
    for email, name, role, inst in [
        ("inst1@demo.com", "Demo Institute Admin", INSTITUTION, "1-1001"),
        ("inst2@demo.com", "Sample College Admin", INSTITUTION, "1-2002"),
        ("inst3@demo.com", "Scan Test Admin", INSTITUTION, "1-3003"),
        ("officer@demo.com", "Scrutiny Officer", SCRUTINY, None),
        ("verifier@demo.com", "Verification Officer", VERIFIER, None),
        ("admin@demo.com", "System Admin", ADMIN, None)
    ]:
        db.session.add(User(email=email, name=name, role=role, institution_id=inst, password_hash=pw))
    db.session.commit()

    store = S.storage()
    meta = {
        "APP-001": ("SV-TEST-001", "1-1001", "B.Tech Computer Engineering", "120", "Private"),
        "APP-002": ("SV-TEST-002", "1-2002", "B.Tech Mechanical Engineering", "120", "Autonomous"),
        "APP-003": ("SV-TEST-003", "1-3003", "B.Tech Civil Engineering", "60", "Private"),
        "APP-004": ("SV-TEST-004", "1-3003", "B.Tech Civil Engineering", "60", "Private")
    }

    for src, (aid, inst, prog, intake, itype) in meta.items():
        a = Application(
            id=aid, institution_id=inst, category="EoA", status="Submitted",
            programme=prog, intake=intake, institution_type=itype,
            submitted_at=datetime.now()
        )
        db.session.add(a)
        db.session.flush()

        src_dir = os.path.join(BASE, "data", "synthetic", src)
        if os.path.isdir(src_dir):
            for fn in sorted(os.listdir(src_dir)):
                with open(os.path.join(src_dir, fn), "rb") as f:
                    store.save(aid, fn, f.read())

        S.audit(aid, "application_created", "synthetic test data", actor="seed")
        S.snapshot(a, "created", actor="seed")
        db.session.commit()
        S.queue_validation(a, async_ok=False)

    print("Seeded. Password for every demo login: demo123")
    print("  institutions: inst1@demo.com, inst2@demo.com, inst3@demo.com")
    print("  staff: officer@demo.com, verifier@demo.com, admin@demo.com")


def purge():
    days = int(S.get_setting("retention_days") or 365)
    cutoff = datetime.now() - timedelta(days=days)
    n = 0
    for a in Application.query.filter(Application.closed_at != None, Application.closed_at < cutoff):  # noqa: E711
        S.storage().delete_app(a.id)
        Document.query.filter_by(app_id=a.id).delete()
        a.report_json = "{}"
        S.audit(a.id, "retention_purge", f"documents securely deleted after {days} days")
        n += 1
    db.session.commit()
    print(f"Purged {n} application(s) older than {days} days.")


if __name__ == "__main__":
    import uvicorn
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "seed":
        seed()
    elif cmd == "purge":
        purge()
    else:
        port = int(os.environ.get("PORT", 5000))
        uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=True)
