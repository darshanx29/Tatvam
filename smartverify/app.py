"""AICTE SmartVerify - Flask app.   python app.py seed   then   python app.py"""
import json, os, secrets, shutil, sys, time, uuid
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file,
                   session, url_for)
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

import reporting
import services as S
from core import records, rules_engine, security
from models import (ADMIN, INSTITUTION, OFFICERS, OPEN_STATES, ROLE_LABEL, SCRUTINY, VERIFIER, Application, ApplicationVersion,
                    AuditEvent, Document, ExtractedField, Finding, Notification, ProcessingRun, ReviewAction, RuleVersion, User,
                    VerificationRecord, db)

BASE = os.path.dirname(os.path.abspath(__file__))
_fails = {}          # login throttling: (ip, email) -> [timestamps]   (in-memory; use Redis behind several workers)


def create_app(config=None):
    app = Flask(__name__)
    key = os.environ.get("SECRET_KEY")
    if not key:
        key = secrets.token_hex(32)          # per-process; sessions reset on restart. Set SECRET_KEY in production.
        print("WARNING: SECRET_KEY not set - using a temporary random key.", file=sys.stderr)
    app.config.update(
        BASE=BASE, UPLOADS=os.path.join(BASE, "uploads"), SECRET_KEY=key,
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE, "smartverify.db")),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1", PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        ASYNC_PROCESSING=os.environ.get("ASYNC_PROCESSING", "1") == "1", LOGIN_MAX_FAILS=5, LOGIN_WINDOW_S=600)
    if config:
        app.config.update(config)
    db.init_app(app)
    register(app)
    with app.app_context():
        db.create_all()
        S.seed_rules()
    return app


# ============================================================================ helpers
def current_user():
    if hasattr(g, "_user"):
        return g._user
    u = db.session.get(User, session["uid"]) if "uid" in session else None
    if u and (not u.active or session.get("epoch") != u.session_epoch):
        session.clear(); u = None            # access revoked / password changed -> session dead
    g._user = u
    return u


def wants_json():
    return request.path.startswith("/api/")


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                return (jsonify(error="authentication required"), 401) if wants_json() else redirect(url_for("login"))
            if roles and u.role not in roles:
                return (jsonify(error="forbidden"), 403) if wants_json() else abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def get_app_or_403(app_id):
    a = db.session.get(Application, app_id) or abort(404)
    u = current_user()
    if u.role == INSTITUTION and u.institution_id != a.institution_id:
        abort(403)                            # institutions only see their own records
    if u.role != INSTITUTION and a.status == "Draft":
        abort(404)                            # drafts are private to the institution
    return a


def get_doc_or_403(did):
    d = db.session.get(Document, did) or abort(404)
    return d, get_app_or_403(d.app_id)


def fail(msg, code=400):
    if wants_json():
        return jsonify(error=msg), code
    flash(msg, "error")
    return None


def csrf_input():
    return Markup('<input type="hidden" name="csrf_token" value="%s">' % session.setdefault("csrf", security.new_csrf()))


def can_manage(a, u):
    return u.role == INSTITUTION and u.institution_id == a.institution_id


def back(app_id):
    return redirect(url_for("view_application", app_id=app_id))


# ============================================================================ wiring (hooks, filters, routes)
def register(app):
    @app.before_request
    def csrf_and_load():
        session.setdefault("csrf", security.new_csrf())
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not security.csrf_ok(session.get("csrf"), sent):
                if wants_json():
                    return jsonify(error="CSRF token missing or invalid"), 400
                return render_template("error.html", msg="Your session form expired. Please go back and try again."), 400

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if "uid" in session:
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def inject():
        u = current_user()
        return {"user": u, "ROLE_LABEL": ROLE_LABEL, "OFFICERS": OFFICERS, "INSTITUTION": INSTITUTION, "ADMIN": ADMIN,
                "csrf_input": csrf_input, "OPEN_STATES": OPEN_STATES, "new_token": lambda: uuid.uuid4().hex}

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", msg="You are not authorized to view this record."), 403

    @app.errorhandler(404)
    def notfound(_):
        if wants_json():
            return jsonify(error="not found"), 404
        return render_template("error.html", msg="That page or record could not be found."), 404

    @app.errorhandler(413)
    def toolarge(_):
        return render_template("error.html", msg="The upload is too large."), 413

    # ------------------------------------------------------------------ public / auth
    @app.route("/")
    def index():
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            key = (request.remote_addr, email)
            now = time.time()
            recent = [t for t in _fails.get(key, []) if now - t < app.config["LOGIN_WINDOW_S"]]
            if len(recent) >= app.config["LOGIN_MAX_FAILS"]:
                S.audit("SYSTEM", "login_throttled", email)
                db.session.commit()
                flash("Too many failed attempts. Try again in a few minutes.", "error")
                return render_template("login.html"), 429
            u = User.query.filter_by(email=email).first()
            if u and u.active and check_password_hash(u.password_hash, request.form.get("password", "")):
                _fails.pop(key, None)
                csrf = session.get("csrf")
                session.clear(); session.permanent = True
                session.update(uid=u.id, email=u.email, epoch=u.session_epoch, csrf=csrf or security.new_csrf())
                S.audit("SYSTEM", "login_success", u.email); db.session.commit()
                return redirect(url_for("dashboard"))
            _fails[key] = recent + [now]
            S.audit("SYSTEM", "login_failed", email); db.session.commit()
            flash("Invalid email or password", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        if current_user():
            S.audit("SYSTEM", "logout", ""); db.session.commit()
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------------ dashboard
    @app.route("/dashboard")
    @login_required()
    def dashboard():
        u = current_user()
        q = Application.query
        if u.role == INSTITUTION:
            q = q.filter_by(institution_id=u.institution_id)
        else:
            q = q.filter(Application.status != "Draft")
        allapps = q.order_by(Application.created_at.desc()).all()
        text, status = request.args.get("q", "").strip().lower(), request.args.get("status", "")
        apps = [a for a in allapps if (not text or text in a.id.lower() or text in (a.institution_id or "").lower()) and (not status or a.status == status)]
        page = max(int(request.args.get("page", 1) or 1), 1)
        per = 10
        pages = max((len(apps) + per - 1) // per, 1)
        ids = [a.id for a in apps]
        counts = {}
        if ids:
            for f in Finding.query.filter(Finding.app_id.in_(ids), Finding.state.in_(OPEN_STATES)):
                counts[f.app_id] = counts.get(f.app_id, 0) + 1
        alerts = AuditEvent.query.filter(AuditEvent.app_id.in_([a.id for a in allapps])).order_by(AuditEvent.ts.desc(), AuditEvent.id.desc()).limit(8).all() if allapps else []
        high = Finding.query.filter(Finding.app_id.in_([a.id for a in allapps]), Finding.state == "open", Finding.severity == "high").order_by(Finding.id.desc()).limit(5).all() if allapps and u.role != INSTITUTION else []
        notes = Notification.query.filter_by(institution_id=u.institution_id, read=False).order_by(Notification.id.desc()).all() if u.role == INSTITUTION else []
        return render_template("dashboard.html", apps=apps[(page - 1) * per: page * per], counts=counts, alerts=alerts, high=high, notes=notes,
                               kpi=S.kpis(allapps), ev=S.evaluation_report(), page=page, pages=pages, q=text, status=status,
                               statuses=sorted({a.status for a in allapps}))

    @app.route("/notifications/read", methods=["POST"])
    @login_required(INSTITUTION)
    def notifications_read():
        Notification.query.filter_by(institution_id=current_user().institution_id).update({"read": True})
        db.session.commit()
        return redirect(url_for("dashboard"))

    # ------------------------------------------------------------------ application intake
    @app.route("/applications/new", methods=["GET", "POST"])
    @login_required(INSTITUTION)
    def new_application():
        u = current_user()
        rec = records.get_record(u.institution_id) or {}
        if request.method == "POST":
            a = S.create_application(u, request.form)
            saved, rej = S.store_uploads(a, request.files.getlist("files"))
            for r in rej: flash(r, "error")
            if request.form.get("action") == "submit":
                miss = S.missing_for_submit(a)
                if miss:
                    db.session.commit()
                    flash("Saved as draft. Still needed before submission: " + ", ".join(miss), "error")
                    return back(a.id)
                submit(a)
                flash("Application submitted; preliminary checks are running.", "ok")
            else:
                flash("Draft saved.", "ok")
            db.session.commit()
            return back(a.id)
        return render_template("new_application.html", cats=S.categories(), rec=rec)

    def submit(a):
        a.status, a.submitted_at = "Submitted", datetime.now()
        S.snapshot(a, "submitted"); S.audit(a.id, "application_submitted", "")
        db.session.commit()
        S.queue_validation(a)

    @app.route("/applications/<app_id>/edit", methods=["POST"])
    @login_required(INSTITUTION)
    def edit_application(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.edit_application(a, request.form)
        saved, rej = S.store_uploads(a, request.files.getlist("files")) if request.files else (0, [])
        for r in rej: flash(r, "error")
        flash(msg, "ok" if ok else "error")
        db.session.commit()
        return back(a.id)

    @app.route("/applications/<app_id>/submit", methods=["POST"])
    @login_required(INSTITUTION)
    def submit_application(app_id):
        a = get_app_or_403(app_id)
        if a.status != "Draft":
            flash("Already submitted.", "error"); return back(a.id)
        miss = S.missing_for_submit(a)
        if miss:
            flash("Cannot submit yet. Missing: " + ", ".join(miss), "error"); return back(a.id)
        submit(a)
        flash("Application submitted; preliminary checks are running.", "ok")
        return back(a.id)

    @app.route("/applications/<app_id>/upload", methods=["POST"])
    @login_required(INSTITUTION)
    def upload(app_id):
        a = get_app_or_403(app_id)
        saved, rej = S.store_uploads(a, request.files.getlist("files"))
        for r in rej: flash(r, "error")
        if a.status == "Closed in prototype":
            a.status, a.closed_at = "Submitted", None
        db.session.commit()
        if saved and a.status != "Draft":
            S.queue_validation(a)
            flash(f"{saved} file(s) uploaded; checks are re-running.", "ok")
        elif saved:
            flash(f"{saved} file(s) added to the draft.", "ok")
        return back(a.id)

    @app.route("/applications/<app_id>/validate", methods=["POST"])
    @login_required(INSTITUTION, SCRUTINY, VERIFIER, ADMIN)
    def revalidate(app_id):
        a = get_app_or_403(app_id)
        if a.status == "Draft":
            flash("Submit the draft first.", "error"); return back(a.id)
        run, started = S.queue_validation(a)
        flash("Validation started. Earlier review decisions are preserved." if started else "A validation run is already in progress.", "ok")
        return back(a.id)

    @app.route("/applications/<app_id>/status.json")
    @login_required()
    def run_status(app_id):
        a = get_app_or_403(app_id)
        run = ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first()
        return jsonify(app_status=a.status, run=({"status": run.status, "progress": run.progress, "message": run.message} if run else None))

    # ------------------------------------------------------------------ application workspace
    @app.route("/applications/<app_id>")
    @login_required()
    def view_application(app_id):
        a = get_app_or_403(app_id)
        u = current_user()
        docs = Document.query.filter_by(app_id=a.id).order_by(Document.name).all()
        have = {d.doc_type for d in docs}
        checklist = [(t, title, rid, t in have) for t, title, rid in S.required_docs(a)]
        findings = Finding.query.filter_by(app_id=a.id).order_by(Finding.id).all()
        acts = ReviewAction.query.filter_by(app_id=a.id).order_by(ReviewAction.ts).all()
        by_f = {}
        for x in acts:
            if x.finding_id: by_f.setdefault(x.finding_id, []).append(x)
        run = ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first()
        S.audit(a.id, "application_viewed", u.email); db.session.commit()
        return render_template("application.html", a=a, docs=docs, checklist=checklist, findings=findings, by_f=by_f,
                               verifications=S.effective_verifications(a), run=run, versions=ApplicationVersion.query.filter_by(app_id=a.id).order_by(ApplicationVersion.id.desc()).all(),
                               notes=[x for x in acts if x.action in ("observation", "recommendation", "close")], stored=S.storage().names(a.id),
                               cats=S.categories(), recs=S.RECOMMENDATIONS, mine=can_manage(a, u), uploaded_names=[d.name for d in docs],
                               infra_docs=[d for d in docs if d.quality])

    @app.route("/applications/<app_id>/compliance")
    @login_required()
    def compliance(app_id):
        a = get_app_or_403(app_id)
        rep = a.report
        res = rep.get("assessment", [])
        order = {"FAIL": 0, "INCONCLUSIVE": 1, "PASS": 2, "NOT_APPLICABLE": 3}
        res = sorted(res, key=lambda x: (order.get(x["status"], 9), x["rule_id"]))
        summary = {"compliant": sum(x["status"] == "PASS" for x in res), "deficient": sum(x["status"] == "FAIL" for x in res),
                   "inconclusive": sum(x["status"] == "INCONCLUSIVE" for x in res)}
        refer = [x for x in res if x["status"] == "INCONCLUSIVE" and x.get("rule_type") == "infra_quality"]
        S.audit(a.id, "compliance_viewed", ""); db.session.commit()
        return render_template("compliance.html", a=a, res=res, summary=summary, refer=refer, rules_used=rep.get("rules_used", []))

    # ------------------------------------------------------------------ documents (original + extracted data)
    @app.route("/documents/<int:did>")
    @login_required()
    def doc_view(did):
        d, a = get_doc_or_403(did)
        data = S.storage().read(a.id, d.name)
        npages = 1
        if d.name.lower().endswith(".pdf"):
            import pymupdf
            npages = max(pymupdf.open(stream=data, filetype="pdf").page_count, 1)
        page = min(max(int(request.args.get("page", 1) or 1), 1), npages)
        S.audit(a.id, "document_viewed", d.name); db.session.commit()
        ver = next((v for v in S.effective_verifications(a) if v["document"] == d.name), None)
        flags = Finding.query.filter(Finding.app_id == a.id, Finding.kind == "anomaly", Finding.state != "resolved", Finding.source.contains(d.name)).all()
        return render_template("doc_view.html", a=a, d=d, page=page, npages=npages, ver=ver, flags=flags, qr=json.loads(d.qr_json or "[]"), mine=can_manage(a, current_user()))

    @app.route("/documents/<int:did>/file")
    @login_required()
    def doc_file(did):
        d, a = get_doc_or_403(did)
        data = S.storage().read(a.id, d.name)
        S.audit(a.id, "document_downloaded", d.name); db.session.commit()
        mt = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[d.name.rsplit(".", 1)[-1].lower()]
        return send_file(BytesIO(data), mimetype=mt, download_name=d.name, as_attachment=request.args.get("dl") == "1")

    @app.route("/documents/<int:did>/page/<int:n>.png")
    @login_required()
    def doc_page(did, n):
        from PIL import Image
        d, a = get_doc_or_403(did)
        data = S.storage().read(a.id, d.name)
        if d.name.lower().endswith(".pdf"):
            import pymupdf
            doc = pymupdf.open(stream=data, filetype="pdf")
            pix = doc[max(min(n, doc.page_count), 1) - 1].get_pixmap(dpi=100)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(BytesIO(data)).convert("RGB")
            if img.width > 1600:
                img = img.resize((1600, int(img.height * 1600 / img.width)))
        out = BytesIO(); img.save(out, "PNG"); out.seek(0)
        return send_file(out, mimetype="image/png")

    @app.route("/fields/<int:fid>/correct", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def correct_field(fid):
        f = db.session.get(ExtractedField, fid) or abort(404)
        a = get_app_or_403(f.document.app_id)
        ok, msg = S.correct_field(a, f, request.form.get("value", ""), request.form.get("reason", ""), current_user().email)
        db.session.commit()
        flash(msg, "ok" if ok else "error")
        if ok:
            S.queue_validation(a)
        return redirect(url_for("doc_view", did=f.doc_id))

    # ------------------------------------------------------------------ officer review
    @app.route("/findings/<int:fid>/review", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def review(fid):
        f = db.session.get(Finding, fid) or abort(404)
        get_app_or_403(f.app_id)
        ok, msg = S.apply_review(f, current_user().email, request.form.get("action"), request.form.get("reason", ""), request.form.get("token"))
        db.session.commit()
        flash(msg, "ok" if ok else "error")
        return back(f.app_id)

    @app.route("/findings/<int:fid>/respond", methods=["POST"])
    @login_required(INSTITUTION)
    def respond(fid):
        f = db.session.get(Finding, fid) or abort(404)
        a = get_app_or_403(f.app_id)
        ok, msg = S.add_note(a, current_user().email, "institution_response", f"[{f.rule_id} / {f.source}] " + request.form.get("text", ""), request.form.get("token"))
        if ok:
            last = ReviewAction.query.filter_by(app_id=a.id, action="institution_response", finding_id=None).order_by(ReviewAction.id.desc()).first()
            if last: last.finding_id = f.id
        db.session.commit()
        flash("Response recorded for the officer." if ok else msg, "ok" if ok else "error")
        return back(a.id)

    @app.route("/applications/<app_id>/observation", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def observation(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.add_note(a, current_user().email, "observation", request.form.get("text", ""), request.form.get("token"))
        db.session.commit(); flash(msg, "ok" if ok else "error")
        return back(a.id)

    @app.route("/applications/<app_id>/recommendation", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def recommendation(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.set_recommendation(a, current_user().email, request.form.get("choice"), request.form.get("note", ""), request.form.get("token"))
        db.session.commit(); flash(msg, "ok" if ok else "error")
        return back(a.id)

    @app.route("/applications/<app_id>/close", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def close_app(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.close_in_prototype(a, current_user().email)
        db.session.commit(); flash(msg, "ok" if ok else "error")
        return back(a.id)

    @app.route("/applications/<app_id>/reverify", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def reverify(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.reverify(a, request.form.get("document", ""))
        db.session.commit(); flash(msg, "ok" if ok else "error")
        return back(a.id)

    @app.route("/applications/<app_id>/manual-verify", methods=["POST"])
    @login_required(VERIFIER, SCRUTINY)
    def manual_verify(app_id):
        a = get_app_or_403(app_id)
        ok, msg = S.record_manual_verification(a, request.form.get("document", ""), request.form.get("outcome", ""), request.form.get("reference", ""),
                                               request.form.get("note", ""), current_user().email)
        db.session.commit(); flash(msg, "ok" if ok else "error")
        return back(a.id)

    # ------------------------------------------------------------------ audit & reports
    @app.route("/audit/<app_id>")
    @login_required()
    def audit_view(app_id):
        a = get_app_or_403(app_id)
        ev = AuditEvent.query.filter_by(app_id=a.id).order_by(AuditEvent.ts.desc(), AuditEvent.id.desc()).all()
        return render_template("audit.html", a=a, events=ev, title="Audit history · " + a.id)

    def report_parts(a, officer):
        findings = Finding.query.filter(Finding.app_id == a.id, Finding.state != "resolved").order_by(Finding.id).all()
        acts = ReviewAction.query.filter_by(app_id=a.id).order_by(ReviewAction.ts).all()
        return findings, acts, S.effective_verifications(a), a.report.get("assessment", [])

    @app.route("/applications/<app_id>/report")
    @login_required()
    def report(app_id):
        a = get_app_or_403(app_id)
        f, acts, v, _ = report_parts(a, False)
        S.audit(a.id, "report_viewed", ""); db.session.commit()
        return render_template("report.html", a=a, findings=f, acts=acts, verifications=v, rec_label=S.RECOMMENDATIONS.get(a.recommendation))

    @app.route("/applications/<app_id>/report.<fmt>")
    @login_required()
    def report_export(app_id, fmt):
        a = get_app_or_403(app_id)
        officer = current_user().role != INSTITUTION
        f, acts, v, assess = report_parts(a, officer)
        d = reporting.data(a, f, acts, v, assess, officer)
        S.audit(a.id, "report_exported", fmt); db.session.commit()
        if fmt == "json":
            return Response(reporting.to_json(d), mimetype="application/json", headers={"Content-Disposition": f"attachment; filename={a.id}-report.json"})
        if fmt == "csv":
            return Response(reporting.to_csv(d), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={a.id}-report.csv"})
        if fmt == "pdf":
            return Response(reporting.to_pdf(d), mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={a.id}-report.pdf"})
        abort(404)

    # ------------------------------------------------------------------ administration
    @app.route("/admin/rules")
    @login_required(ADMIN)
    def admin_rules():
        latest = S.latest_rule_versions()
        today = datetime.now()
        in_force = {r["id"] for r in rules_engine.select_versions(S.all_rule_defs(), today)}
        return render_template("admin_rules.html", rules=sorted(latest.values(), key=lambda r: r.rule_id), in_force=in_force)

    @app.route("/admin/rules/new", methods=["GET", "POST"])
    @app.route("/admin/rules/<rule_id>", methods=["GET", "POST"])
    @login_required(ADMIN)
    def admin_rule_edit(rule_id=None):
        prev = S.latest_rule_versions().get(rule_id) if rule_id else None
        if rule_id and not prev:
            abort(404)
        template = prev.definition if prev else {"id": "R-NEW-01", "version": "1.0", "title": "", "type": "required_doc", "categories": ["EoA"], "severity": "medium",
                                                  "clause": "<<fill from Approval Process Handbook>>", "remedy": "", "doc_type": "", "effective_from": datetime.now().date().isoformat(),
                                                  "effective_to": None, "active": True, "applies_when": {}}
        text = json.dumps(template, indent=2)
        if request.method == "POST":
            text = request.form.get("definition", "")
            try:
                defn = json.loads(text)
            except ValueError as e:
                flash(f"Not valid JSON: {e}", "error")
                return render_template("admin_rule_edit.html", rule_id=rule_id, text=text, history=S.rule_history(rule_id) if rule_id else [], types=rules_engine.TYPES)
            if rule_id and defn.get("id") != rule_id:
                flash("The rule id cannot be changed; create a new rule instead.", "error")
            elif not rule_id and S.latest_rule_versions().get(defn.get("id")):
                flash("That rule id already exists - edit the existing rule.", "error")
            else:
                ok, msg = S.save_rule_version(defn, current_user().email, request.form.get("note", ""))
                if ok:
                    db.session.commit(); flash(f"Saved {defn['id']} as version {msg}. Earlier versions remain for audit.", "ok")
                    return redirect(url_for("admin_rules"))
                flash(msg, "error")
        return render_template("admin_rule_edit.html", rule_id=rule_id, text=text, history=S.rule_history(rule_id) if rule_id else [], types=rules_engine.TYPES)

    @app.route("/admin/users", methods=["GET", "POST"])
    @login_required(ADMIN)
    def admin_users():
        if request.method == "POST":
            email, role = request.form.get("email", "").strip().lower(), request.form.get("role")
            pw = request.form.get("password", "")
            prob = security.password_problem(pw)
            if not email or role not in ROLE_LABEL:
                flash("Email and a valid role are required.", "error")
            elif prob:
                flash(prob, "error")
            elif User.query.filter_by(email=email).first():
                flash("A user with that email already exists.", "error")
            elif role == INSTITUTION and not request.form.get("institution_id", "").strip():
                flash("Institution users need an institution ID.", "error")
            else:
                db.session.add(User(email=email, name=request.form.get("name") or email, role=role, password_hash=generate_password_hash(pw),
                                    institution_id=request.form.get("institution_id", "").strip() or None))
                S.audit("SYSTEM", "user_created", f"{email} ({role})"); db.session.commit(); flash("User created.", "ok")
        return render_template("admin_users.html", users=User.query.order_by(User.id).all())

    @app.route("/admin/users/<int:uid>/toggle", methods=["POST"])
    @login_required(ADMIN)
    def admin_user_toggle(uid):
        t = db.session.get(User, uid) or abort(404)
        if t.id == current_user().id:
            flash("You cannot disable your own account.", "error")
        else:
            t.active = not t.active; t.session_epoch += 1          # revokes live sessions immediately
            S.audit("SYSTEM", "user_enabled" if t.active else "access_revoked", t.email); db.session.commit()
            flash(f"{t.email} {'enabled' if t.active else 'disabled; sessions revoked'}.", "ok")
        return redirect(url_for("admin_users"))

    @app.route("/admin/users/<int:uid>/password", methods=["POST"])
    @login_required(ADMIN)
    def admin_user_password(uid):
        t = db.session.get(User, uid) or abort(404)
        prob = security.password_problem(request.form.get("password", ""))
        if prob:
            flash(prob, "error")
        else:
            t.password_hash = generate_password_hash(request.form["password"]); t.session_epoch += 1
            S.audit("SYSTEM", "password_reset", t.email); db.session.commit(); flash("Password reset; the user's sessions were revoked.", "ok")
        return redirect(url_for("admin_users"))

    @app.route("/admin/settings", methods=["GET", "POST"])
    @login_required(ADMIN)
    def admin_settings():
        if request.method == "POST":
            for k in S.SETTING_DEFAULTS:
                if k in request.form:
                    S.set_setting(k, request.form[k].strip())
            S.audit("SYSTEM", "settings_changed", ", ".join(S.SETTING_DEFAULTS)); db.session.commit(); flash("Settings saved.", "ok")
        vals = {k: S.get_setting(k) for k in S.SETTING_DEFAULTS}
        return render_template("admin_settings.html", vals=vals, ev=S.evaluation_report(), runs=ProcessingRun.query.order_by(ProcessingRun.id.desc()).limit(10).all(),
                               adapter="MOCK-ISSUER-REGISTRY (data/mock_registry.json)")

    @app.route("/admin/audit")
    @login_required(ADMIN)
    def admin_audit():
        ev = AuditEvent.query.filter((AuditEvent.app_id == "SYSTEM") | (AuditEvent.app_id == None)).order_by(AuditEvent.id.desc()).limit(300).all()   # noqa: E711
        return render_template("audit.html", a=None, events=ev, title="System audit (administration, sign-ins)")

    register_api(app)
    register_cli(app)


# ============================================================================ REST API  /api/v1
def register_api(app):
    def allowed(a):
        u = current_user()
        return not (u.role == INSTITUTION and u.institution_id != a.institution_id)

    @app.route("/api/v1/me")
    @login_required()
    def api_me():
        u = current_user()
        return jsonify(email=u.email, role=u.role, institution_id=u.institution_id, csrf_token=session["csrf"])

    @app.route("/api/v1/applications", methods=["POST"])
    @login_required(INSTITUTION)
    def api_create():
        body = request.get_json(silent=True) or {}
        a = S.create_application(current_user(), body)
        db.session.commit()
        return jsonify(a.as_dict()), 201

    @app.route("/api/v1/applications")
    @login_required()
    def api_list():
        u = current_user()
        q = Application.query
        q = q.filter_by(institution_id=u.institution_id) if u.role == INSTITUTION else q.filter(Application.status != "Draft")
        page, per = max(int(request.args.get("page", 1) or 1), 1), min(int(request.args.get("per_page", 25) or 25), 100)
        rows = q.order_by(Application.created_at.desc()).offset((page - 1) * per).limit(per).all()
        return jsonify(page=page, items=[a.as_dict() for a in rows])

    @app.route("/api/v1/applications/<app_id>")
    @login_required()
    def api_get(app_id):
        a = get_app_or_403(app_id)
        return jsonify(a.as_dict())

    @app.route("/api/v1/applications/<app_id>/documents", methods=["POST"])
    @login_required(INSTITUTION)
    def api_upload(app_id):
        a = get_app_or_403(app_id)
        saved, rej = S.store_uploads(a, request.files.getlist("files"))
        db.session.commit()
        return jsonify(saved=saved, rejected=rej), (201 if saved else 400)

    @app.route("/api/v1/applications/<app_id>/checklist")
    @login_required()
    def api_checklist(app_id):
        a = get_app_or_403(app_id)
        have = {d.doc_type for d in Document.query.filter_by(app_id=a.id)}
        return jsonify(items=[{"doc_type": t, "title": title, "rule_id": rid, "present": t in have} for t, title, rid in S.required_docs(a)])

    @app.route("/api/v1/applications/<app_id>/validate", methods=["POST"])
    @login_required(INSTITUTION, SCRUTINY, VERIFIER, ADMIN)
    def api_validate(app_id):
        a = get_app_or_403(app_id)
        if a.status == "Draft":
            return jsonify(error="submit the draft first"), 409
        run, started = S.queue_validation(a)
        return jsonify(run_id=run.id, started=started, status=run.status), 202

    @app.route("/api/v1/applications/<app_id>/status")
    @login_required()
    def api_status(app_id):
        a = get_app_or_403(app_id)
        run = ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first()
        return jsonify(application_status=a.status, run=({"status": run.status, "progress": run.progress, "message": run.message} if run else None))

    @app.route("/api/v1/applications/<app_id>/findings")
    @login_required()
    def api_findings(app_id):
        a = get_app_or_403(app_id)
        officer = current_user().role != INSTITUTION
        rows = Finding.query.filter(Finding.app_id == a.id, Finding.state != "resolved").order_by(Finding.id).all()
        return jsonify(items=[f.as_dict(officer) for f in rows])

    @app.route("/api/v1/documents/<int:did>/verify", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def api_verify(did):
        d, a = get_doc_or_403(did)
        ok, msg = S.reverify(a, d.name)
        db.session.commit()
        return jsonify(ok=ok, message=msg), (200 if ok else 409)

    @app.route("/api/v1/findings/<int:fid>/review", methods=["POST"])
    @login_required(SCRUTINY, VERIFIER)
    def api_review(fid):
        f = db.session.get(Finding, fid) or abort(404)
        get_app_or_403(f.app_id)
        body = request.get_json(silent=True) or {}
        ok, msg = S.apply_review(f, current_user().email, body.get("action"), body.get("reason", ""), body.get("token"))
        db.session.commit()
        return jsonify(ok=ok, message=msg, state=f.state), (200 if ok else 400)

    @app.route("/api/v1/applications/<app_id>/audit")
    @login_required()
    def api_audit(app_id):
        a = get_app_or_403(app_id)
        ev = AuditEvent.query.filter_by(app_id=a.id).order_by(AuditEvent.id).all()
        return jsonify(items=[{"ts": e.ts.isoformat(timespec="seconds"), "actor": e.actor, "event": e.event, "detail": e.detail} for e in ev])

    @app.route("/api/v1/rules")
    @login_required(SCRUTINY, VERIFIER, ADMIN)
    def api_rules():
        return jsonify(items=[rv.definition for rv in S.latest_rule_versions().values()])


# ============================================================================ CLI
def register_cli(app):
    pass


def seed(app):
    with app.app_context():
        db.drop_all(); db.create_all()
        shutil.rmtree(app.config["UPLOADS"], ignore_errors=True)
        S.seed_rules()
        if not os.path.isdir(os.path.join(BASE, "data", "synthetic", "APP-001")):
            import gen_synthetic
            gen_synthetic.app001(); gen_synthetic.app002(); gen_synthetic.app003(); gen_synthetic.app004()
            json.dump(gen_synthetic.REG, open(os.path.join(BASE, "data", "mock_registry.json"), "w"), indent=2)
        pw = generate_password_hash("demo123")        # DEMO ONLY - the password policy applies to accounts created via Admin
        for email, name, role, inst in [("inst1@demo.com", "Demo Institute Admin", INSTITUTION, "1-1001"),
                                        ("inst2@demo.com", "Sample College Admin", INSTITUTION, "1-2002"),
                                        ("inst3@demo.com", "Scan Test Admin", INSTITUTION, "1-3003"),
                                        ("officer@demo.com", "Scrutiny Officer", SCRUTINY, None),
                                        ("verifier@demo.com", "Verification Officer", VERIFIER, None),
                                        ("admin@demo.com", "System Admin", ADMIN, None)]:
            db.session.add(User(email=email, name=name, role=role, institution_id=inst, password_hash=pw))
        db.session.commit()
        store = S.storage()
        meta = {"APP-001": ("SV-TEST-001", "1-1001", "B.Tech Computer Engineering", "120", "Private"),
                "APP-002": ("SV-TEST-002", "1-2002", "B.Tech Mechanical Engineering", "120", "Autonomous"),
                "APP-003": ("SV-TEST-003", "1-3003", "B.Tech Civil Engineering", "60", "Private"),
                "APP-004": ("SV-TEST-004", "1-3003", "B.Tech Civil Engineering", "60", "Private")}
        for src, (aid, inst, prog, intake, itype) in meta.items():
            a = Application(id=aid, institution_id=inst, category="EoA", status="Submitted", programme=prog, intake=intake, institution_type=itype,
                            submitted_at=datetime.now())
            db.session.add(a); db.session.flush()
            for fn in sorted(os.listdir(os.path.join(BASE, "data", "synthetic", src))):
                store.save(aid, fn, open(os.path.join(BASE, "data", "synthetic", src, fn), "rb").read())
            S.audit(aid, "application_created", "synthetic test data"); S.snapshot(a, "created")
            db.session.commit()
            S.queue_validation(a, async_ok=False)
        print("Seeded. Password for every demo login: demo123\n  institutions: inst1@demo.com, inst2@demo.com, inst3@demo.com\n"
              "  staff: officer@demo.com, verifier@demo.com, admin@demo.com\nDemo passwords are for local synthetic data only.")


def purge(app):
    """Retention: secure-delete files and rows of CLOSED applications older than the retention window."""
    with app.app_context():
        days = int(S.get_setting("retention_days") or 365)
        cutoff = datetime.now() - timedelta(days=days)
        n = 0
        for a in Application.query.filter(Application.closed_at != None, Application.closed_at < cutoff):   # noqa: E711
            S.storage().delete_app(a.id)
            Document.query.filter_by(app_id=a.id).delete()
            a.report_json = "{}"
            S.audit(a.id, "retention_purge", f"documents securely deleted after {days} days"); n += 1
        db.session.commit()
        print(f"Purged {n} application(s) older than {days} days.")


app = create_app()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "seed":
        seed(app)
    elif cmd == "purge":
        purge(app)
    else:
        app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
