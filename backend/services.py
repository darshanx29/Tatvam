"""Business logic shared by the application endpoints and validation pipeline."""
import contextvars
import json
import os
import re
import statistics
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename

import pipeline
from core import rules_engine, mock_issuer, security
from core.storage import EncryptedLocalStorage
from models import (db, User, Application, ApplicationVersion, Document, ExtractedField, VerificationRecord, Finding,
                    ReviewAction, AuditEvent, RuleVersion, Setting, ProcessingRun, Notification,
                    INSTITUTION, OFFICERS, OPEN_STATES)

BASE = os.path.dirname(os.path.abspath(__file__))
_root_uploads = os.path.abspath(os.path.join(BASE, "..", "uploads"))
_backend_uploads = os.path.join(BASE, "uploads")
_default_uploads = _root_uploads if (os.path.isdir(_root_uploads) and os.listdir(_root_uploads)) else _backend_uploads
UPLOADS_DIR = os.environ.get("UPLOADS_DIR", _default_uploads)

CONCLUSIVE = ("verified", "mismatch_detected", "expired")
INCONCLUSIVE_V = ("pending", "source_unavailable", "manual_review_required")
SETTING_DEFAULTS = {"verify_max_attempts": "3", "qr_allowed_hosts": "", "retention_days": "365"}
REVIEW_STATES = {"accept": "accepted", "dismiss": "dismissed", "escalate": "escalated", "request_evidence": "evidence_requested"}
RECOMMENDATIONS = {
    "no_issues": "No issues found by executed checks",
    "request_rectification": "Request rectification",
    "refer_inspection": "Refer for inspection",
    "escalate": "Escalate to senior officer"
}
_executor = ThreadPoolExecutor(max_workers=2)
_running = set()
_lock = threading.Lock()
_actor_ctx = contextvars.ContextVar("actor", default="system")


def set_current_actor(email: str):
    return _actor_ctx.set(email or "system")


# ------------------------------------------------------------------ settings / audit / storage
def storage():
    return EncryptedLocalStorage(UPLOADS_DIR)


def get_setting(key):
    s = db.session.get(Setting, key)
    return s.value if s else SETTING_DEFAULTS.get(key, "")


def set_setting(key, value):
    s = db.session.get(Setting, key)
    if s:
        s.value = value
    else:
        db.session.add(Setting(key=key, value=value))


import hashlib

GENESIS_HASH = "0" * 64


def actor_name(default=None):
    if default:
        return default
    return _actor_ctx.get()


def audit(app_id, event, detail="", actor=None):
    act = actor or actor_name()
    det = (detail or "")[:1000]
    ts = datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    # Find last entry to get previous hash
    last = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
    prev = last.entry_hash if last and last.entry_hash else GENESIS_HASH
    payload = f"{prev}|{app_id or 'SYSTEM'}|{act}|{event}|{det}|{ts_str}"
    entry_h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    ev = AuditEvent(
        app_id=app_id, actor=act, event=event, detail=det,
        ts=ts, prev_hash=prev, entry_hash=entry_h
    )
    db.session.add(ev)
    db.session.flush()


def verify_audit_chain():
    """Verifies that the entire audit log has unbroken cryptographic hash chaining."""
    events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()
    if not events:
        return True, 0, "No audit events recorded"
    prev = GENESIS_HASH
    for ev in events:
        if ev.prev_hash and ev.prev_hash != prev:
            return False, ev.id, f"Audit chain broken at event #{ev.id}: previous hash mismatch"
        if ev.entry_hash and ev.prev_hash:
            ts_str = ev.ts.strftime("%Y-%m-%d %H:%M:%S") if ev.ts else ""
            expected = hashlib.sha256(
                f"{ev.prev_hash}|{ev.app_id or 'SYSTEM'}|{ev.actor}|{ev.event}|{ev.detail or ''}|{ts_str}".encode("utf-8")
            ).hexdigest()
            if ev.entry_hash != expected:
                return False, ev.id, f"Audit entry #{ev.id} compromised: content hash altered"
        prev = ev.entry_hash or prev
    return True, len(events), f"Audit chain verified: {len(events)} events intact"


# ------------------------------------------------------------------ rules (versioned, DB-backed)
def seed_rules():
    if RuleVersion.query.count():
        return
    for r in rules_engine.load_rules():
        db.session.add(RuleVersion(rule_id=r["id"], version=r["version"], definition_json=json.dumps(r), created_by="seed", note="initial"))
    db.session.commit()


def all_rule_defs():
    return [rv.definition for rv in RuleVersion.query.order_by(RuleVersion.id)]


def latest_rule_versions():
    best = {}
    for rv in RuleVersion.query.order_by(RuleVersion.id):
        best[rv.rule_id] = rv
    return best


def rule_history(rule_id):
    return RuleVersion.query.filter_by(rule_id=rule_id).order_by(RuleVersion.id.desc()).all()


def bump(version):
    p = str(version).split(".")
    return f"{p[0]}.{int(p[1]) + 1}" if len(p) == 2 and p[1].isdigit() else f"{version}.1"


def save_rule_version(defn, actor, note=""):
    """Validates and stores a NEW version; the superseded version gets an effective_to the day before."""
    problems = rules_engine.validate_definition(defn)
    if problems:
        return False, "; ".join(problems)
    prev = latest_rule_versions().get(defn["id"])
    eff = defn.get("effective_from") or date.today().isoformat()
    defn["effective_from"] = eff
    if prev:
        pd = prev.definition
        if rules_engine._ver(defn["version"]) <= rules_engine._ver(pd["version"]):
            defn["version"] = bump(pd["version"])
        end = (rules_engine._iso(eff) - timedelta(days=1)).isoformat()
        if not pd.get("effective_to") or pd["effective_to"] > end:
            pd["effective_to"] = end
            prev.definition_json = json.dumps(pd)
    db.session.add(RuleVersion(rule_id=defn["id"], version=defn["version"], definition_json=json.dumps(defn), created_by=actor, note=note[:300]))
    audit("SYSTEM", "rule_version_saved", f"{defn['id']} v{defn['version']} effective {eff}", actor=actor)
    return True, defn["version"]


def categories():
    cats = {c for r in rules_engine.select_versions(all_rule_defs(), datetime.now()) for c in r["categories"]}
    return sorted(cats) or ["EoA"]


def required_docs(a):
    app = {
        "category": a.category, "institution_id": a.institution_id, "programme": a.programme,
        "academic_year": a.academic_year, "institution_type": a.institution_type
    }
    rules = rules_engine.select_versions(all_rule_defs(), datetime.now())
    return [(r["doc_type"], r["title"].replace(" required", ""), r["id"]) for r in rules
            if r["type"] == "required_doc" and rules_engine.applies(r, app)]


# ------------------------------------------------------------------ applications
def snapshot(a, reason, actor=None):
    n = ApplicationVersion.query.filter_by(app_id=a.id).count() + 1
    db.session.add(ApplicationVersion(app_id=a.id, version=n, actor=actor or actor_name(), reason=reason,
                                      snapshot_json=json.dumps({k: v for k, v in a.as_dict().items() if k not in ("last_run",)})))


def new_app_id():
    n = Application.query.count() + 1
    while db.session.get(Application, "SV-%04d" % n):
        n += 1
    return "SV-%04d" % n


def create_application(user, form):
    a = Application(id=new_app_id(), institution_id=user.institution_id, status="Draft",
                    category=form.get("category") or "EoA", academic_year=form.get("academic_year") or "2026-27",
                    programme=(form.get("programme") or "").strip() or None, intake=(form.get("intake") or "").strip() or None,
                    institution_type=(form.get("institution_type") or "").strip() or None)
    db.session.add(a); db.session.flush()
    audit(a.id, "application_created", f"category={a.category}", actor=user.email)
    snapshot(a, "created", actor=user.email)
    return a


def edit_application(a, form, actor=None):
    if a.status != "Draft":
        return False, "Only drafts can be edited; submitted applications change through rectification uploads."
    for k in ("category", "academic_year", "programme", "intake", "institution_type"):
        if k in form:
            setattr(a, k, (form.get(k) or "").strip() or None)
    audit(a.id, "application_edited", "", actor=actor)
    snapshot(a, "edited", actor=actor)
    return True, "Draft saved."


def missing_for_submit(a):
    miss = [lbl for lbl, v in (("category", a.category), ("academic year", a.academic_year), ("programme", a.programme), ("intake", a.intake)) if not v]
    if not storage().names(a.id):
        miss.append("at least one document")
    return miss


def store_uploads(a, files, actor=None):
    """files: list of UploadFile or FileStorage. Returns (saved_count, [rejection messages])."""
    saved, rejected, store = 0, [], storage()
    files = [f for f in files if f and getattr(f, "filename", None)]
    if len(files) > security.MAX_FILES_PER_UPLOAD:
        return 0, [f"Too many files (max {security.MAX_FILES_PER_UPLOAD})"]
    for f in files:
        fname = getattr(f, "filename", "") or "upload"
        if hasattr(f, "file") and hasattr(f.file, "read"):
            f.file.seek(0)
            data = f.file.read()
        elif hasattr(f, "read"):
            data = f.read()
        else:
            data = bytes(f)
        ok, info = security.validate_upload(fname, data)
        sec_name = secure_filename(fname) or "file"
        if not ok:
            rejected.append(f"{sec_name}: {info}")
            audit(a.id, "upload_rejected", f"{sec_name}: {info}", actor=actor)
            continue
        store.save(a.id, sec_name, data)
        saved += 1
    audit(a.id, "documents_uploaded", f"{saved} file(s) stored, {len(rejected)} rejected", actor=actor)
    return saved, rejected


# ------------------------------------------------------------------ verification
def basis_of(sha, fields):
    g = lambda k: (fields.get(k) or {}).get("value", "")
    return f"{sha}|{g('certificate_no')}|{g('institution_id')}|{g('valid_until')}"


def doc_fields(doc):
    return {f.name: {"value": f.value, "confidence": f.confidence, "page": f.page} for f in doc.fields}


def effective_verifications(a):
    """Latest manual record for the document's current basis, else the latest automatic record."""
    out = []
    for d in Document.query.filter_by(app_id=a.id).order_by(Document.name):
        recs = VerificationRecord.query.filter_by(app_id=a.id, doc_name=d.name).order_by(VerificationRecord.id.desc()).all()
        basis = basis_of(d.sha, doc_fields(d))
        pick = next((r for r in recs if r.manual and r.basis == basis), None) or next((r for r in recs if not r.manual), None)
        if pick:
            out.append(pick.as_dict())
    return out


def reverify(a, doc_name, actor=None):
    """Retry source verification (policy: bounded attempts). Returns (ok, message)."""
    d = Document.query.filter_by(app_id=a.id, name=doc_name).first()
    if not d:
        return False, "Document not found"
    last = VerificationRecord.query.filter_by(app_id=a.id, doc_name=doc_name, manual=False).order_by(VerificationRecord.id.desc()).first()
    if last and last.status in CONCLUSIVE and last.basis == basis_of(d.sha, doc_fields(d)):
        return False, "Source already gave a conclusive answer for this document."
    mx = int(get_setting("verify_max_attempts") or 3)
    attempt = (last.attempt + 1) if last else 1
    if attempt > mx:
        return False, f"Retry limit ({mx}) reached - assign manual verification."
    v = mock_issuer.verify(doc_fields(d), datetime.now(), attempt=attempt)
    db.session.add(VerificationRecord(app_id=a.id, doc_name=doc_name, basis=basis_of(d.sha, doc_fields(d)), source=v["source"],
                                      status=v["status"], reference=v["reference"], detail=v["detail"], attempt=attempt))
    audit(a.id, "verification_requested", f"{doc_name}: {v['status']} (attempt {attempt})", actor=actor)
    sync_findings(a)
    return True, f"Verification result: {v['status'].replace('_', ' ')}"


def record_manual_verification(a, doc_name, outcome, reference, note, actor):
    d = Document.query.filter_by(app_id=a.id, name=doc_name).first()
    if not d or outcome not in ("verified", "mismatch_detected", "expired", "manual_review_required") or not note.strip():
        return False, "Document, outcome and a note are required."
    db.session.add(VerificationRecord(app_id=a.id, doc_name=doc_name, basis=basis_of(d.sha, doc_fields(d)),
                                      source="MANUAL (" + actor + ")", status=outcome, reference=reference or None,
                                      detail=note.strip(), manual=True, verified_by=actor))
    audit(a.id, "manual_verification", f"{doc_name}: {outcome}", actor=actor)
    sync_findings(a)
    return True, "Manual verification recorded."


# ------------------------------------------------------------------ findings
NEXT_V = {
    "mismatch_detected": "Verify source data and document",
    "expired": "Request renewed certificate",
    "source_unavailable": "Retry within policy or assign manual verification",
    "pending": "Await source response or assign manual verification",
    "manual_review_required": "Assign manual verification"
}


def build_findings(rep, verifs):
    out = []
    for f in rep.get("findings", []):
        out.append(dict(kind="infra" if f.get("rule_type") == "infra_quality" else "rule", rule_id=f["rule_id"], rule_version=f["rule_version"],
                        severity=f["severity"], title=f["title"] + ("" if f["status"] == "FAIL" else " (inconclusive)"), source=f["source"],
                        observed=f["observed"], expected=f["expected"], reason=f["reason"], next_step=f["next_step"], clause=f.get("clause")))
    for a in rep.get("anomalies", []):
        out.append(dict(kind="anomaly", rule_id="ANOM-" + a["type"].upper(), rule_version="1.0", severity="medium",
                        title="Possible anomaly (" + a["type"].replace("_", " ") + ")", source=", ".join(a["evidence"]),
                        observed=a["reason"], expected="-", reason=a["note"], private_detail=a.get("private"),
                        next_step="Human review required - preliminary indicator only"))
    for v in verifs:
        if v["status"] != "verified":
            out.append(dict(kind="verification", rule_id="VER-" + v["status"].upper(), rule_version="1.0",
                            severity="high" if v["status"] in ("mismatch_detected", "expired") else "medium",
                            title="Source verification: " + v["status"].replace("_", " "), source=v["document"],
                            observed=v["status"], expected="verified", reason=v["detail"], next_step=NEXT_V.get(v["status"], "Manual review")))
    for o in out:
        o["signature"] = f'{o["kind"]}|{o["rule_id"]}|{o["source"]}|{o["observed"]}'[:500]
    return out


def sync_findings(a, rep=None):
    """Upsert findings by signature (ids + review decisions survive), mark vanished ones 'resolved'."""
    rep = rep if rep is not None else a.report
    verifs = effective_verifications(a)
    new = {f["signature"]: f for f in build_findings(rep, verifs)}
    existing = {f.signature: f for f in Finding.query.filter_by(app_id=a.id)}
    for sig, data in new.items():
        f = existing.get(sig)
        if f:
            for k, v in data.items():
                setattr(f, k, v)
            if f.state == "resolved":
                f.state = "open"
        else:
            db.session.add(Finding(app_id=a.id, state="open", **data))
    for sig, f in existing.items():
        if sig not in new and f.state != "resolved":
            f.state = "resolved"
    rep["verifications"] = verifs
    a.report_json = json.dumps(rep, default=str)
    db.session.flush()
    recompute_status(a)


def recompute_status(a):
    if a.status in ("Draft", "Closed in prototype", "Processing"):
        return
    open_f = Finding.query.filter(Finding.app_id == a.id, Finding.state.in_(OPEN_STATES)).all()
    if any(f.state == "evidence_requested" for f in open_f):
        a.status = "Action required"
    elif any(f.kind != "verification" for f in open_f):
        a.status = "Officer review"
    elif open_f:
        a.status = "Verification pending"
    else:
        a.status = "Preliminary checks complete"


# ------------------------------------------------------------------ the validation run
def queue_validation(a, async_ok=True):
    """Creates a ProcessingRun and executes it (background thread when async). Idempotent while one is running."""
    with _lock:
        if a.id in _running:
            return ProcessingRun.query.filter_by(app_id=a.id).order_by(ProcessingRun.id.desc()).first(), False
        _running.add(a.id)
    run = ProcessingRun(app_id=a.id, status="queued", message="Queued")
    db.session.add(run)
    if a.status != "Draft":
        a.status = "Processing"
    db.session.commit()
    rid, app_id = run.id, a.id
    if async_ok and os.environ.get("ASYNC_PROCESSING", "1") == "1":
        def job():
            try:
                run_validation(app_id, rid)
            finally:
                with _lock:
                    _running.discard(app_id)
                db.session.remove()
        _executor.submit(job)
    else:
        try:
            run_validation(app_id, rid)
        finally:
            with _lock:
                _running.discard(app_id)
            db.session.remove()
    return run, True


def run_validation(app_id, run_id):
    a = db.session.get(Application, app_id)
    run = db.session.get(ProcessingRun, run_id)
    run.status, run.progress = "running", 2
    db.session.commit()
    store, tmp, t0 = storage(), None, datetime.now()
    try:
        old_docs = Document.query.filter_by(app_id=app_id).all()
        overrides, meta, up = {}, {}, {}
        for d in old_docs:
            up[d.name] = (d.uploaded_by, d.uploaded_at)
            for f in d.fields:
                if f.corrected_by:
                    overrides[(d.name, f.name)] = f.value
                    meta[(d.name, f.name)] = (f.corrected_by, f.original_value, f.corrected_at)
        attempts = {}
        for r in VerificationRecord.query.filter_by(app_id=app_id, manual=False).order_by(VerificationRecord.id):
            attempts[r.doc_name] = r
        att = {n: (r.attempt + 1 if r.status in INCONCLUSIVE_V else 1) for n, r in attempts.items()}
        other = []
        for od, oa in db.session.query(Document, Application).join(Application, Application.id == Document.app_id).filter(Document.app_id != app_id).limit(2000):
            cn = next((f.value for f in od.fields if f.name == "certificate_no"), None)
            other.append({"app_id": od.app_id, "name": od.name, "sha": od.sha, "cert_no": cn, "institution_id": oa.institution_id})

        def progress(p, msg):
            run.progress, run.message = p, msg
            db.session.commit()

        tmp = store.materialize(app_id)
        eval_date = datetime.now()
        rules = rules_engine.select_versions(all_rule_defs(), eval_date)
        qr_hosts = [h.strip() for h in get_setting("qr_allowed_hosts").split(",") if h.strip()]
        rep = pipeline.process(tmp, a.category, a.institution_id, eval_date, rules, "auto", overrides, progress,
                               app_extra={"programme": a.programme, "academic_year": a.academic_year, "institution_type": a.institution_type},
                               other_docs=other, qr_hosts=qr_hosts, attempts=att)
        docs_mem = rep.pop("_docs")
        from core import anomaly as an
        for d in old_docs:
            db.session.delete(d)
        db.session.flush()
        by_name = {}
        for dm, dj in zip(docs_mem, rep["documents"]):
            row = Document(app_id=app_id, name=dm["name"], doc_type=dm["doc_type"], class_conf=dm["class_conf"], ocr_method=dm["ocr_method"],
                           mean_conf=dm["mean_conf"], sha=dm["sha"], phash=an.hashes_to_str(dm["phashes"]), size=dm["size"],
                           signature=dm.get("signature"), quality_json=json.dumps(dm["quality"]) if dm.get("quality") else None,
                           qr_json=json.dumps(dm.get("qr", [])), uploaded_by=up.get(dm["name"], (actor_name(), None))[0],
                           uploaded_at=up.get(dm["name"], (None, datetime.now()))[1] or datetime.now())
            for name, f in dm["fields"].items():
                cb = meta.get((dm["name"], name))
                row.fields.append(ExtractedField(name=name, value=f["value"], confidence=f["confidence"], page=f.get("page"),
                                                 bbox_json=json.dumps(f["bbox"]) if f.get("bbox") else None, page_w=f.get("pw"), page_h=f.get("ph"),
                                                 original_value=(cb[1] if cb else None), corrected_by=(cb[0] if cb else None), corrected_at=(cb[2] if cb else None)))
            db.session.add(row); by_name[dm["name"]] = (row, dm)
        db.session.flush()

        for v in rep.get("verifications", []):
            drow, dmem = by_name.get(v["document"], (None, None))
            if drow:
                basis = basis_of(drow.sha, doc_fields(drow))
                last = VerificationRecord.query.filter_by(app_id=app_id, doc_name=v["document"]).order_by(VerificationRecord.id.desc()).first()
                att_num = (last.attempt + 1) if (last and last.status in INCONCLUSIVE_V and last.basis == basis) else 1
                db.session.add(VerificationRecord(app_id=app_id, doc_name=v["document"], basis=basis, source=v["source"], status=v["status"],
                                                  reference=v.get("reference"), detail=v.get("detail"), attempt=att_num))
        db.session.flush()

        sync_findings(a, rep)
        run.status, run.progress, run.message = "done", 100, "Completed"
        a.last_run = datetime.now()
        run.finished = datetime.now()
        run.duration_s = round((run.finished - t0).total_seconds(), 2)
        audit(app_id, "validation_completed", f"{run.duration_s}s, status={a.status}")
    except Exception as e:
        db.session.rollback()
        a = db.session.get(Application, app_id); run = db.session.get(ProcessingRun, run_id)
        run.status, run.message, run.finished = "error", str(e)[:200], datetime.now()
        if a and a.status != "Draft":
            a.status = "Action required"
        audit(app_id, "validation_failed", str(e)[:200])
    finally:
        if tmp: store.cleanup(tmp)
        run = db.session.get(ProcessingRun, run_id)
        if run and run.status == "running": run.status = "error"
        db.session.commit()


def apply_review(f, actor, action, reason, token=None):
    if action not in REVIEW_STATES:
        return False, "Unknown action"
    if not reason or not (reason or "").strip():
        return False, "A justification or reason is required for review."
    if token and ReviewAction.query.filter_by(token=token).first():
        return True, "Decision already recorded"
    a = db.session.get(Application, f.app_id)
    old = f.state
    f.state = REVIEW_STATES[action]
    audit(a.id, f"finding_{action}", f"[{f.rule_id} / {f.source}] {reason.strip()[:150]}", actor=actor)
    if action == "dismiss" and f.severity == "high":
        audit(a.id, "override_logged", f"High-severity finding overridden: [{f.rule_id}] {reason.strip()[:150]}", actor=actor)
    db.session.add(ReviewAction(finding_id=f.id, app_id=f.app_id, actor=actor, action=action, reason=reason.strip(), token=token or None))
    if action == "request_evidence":
        a.status = "Action required"
        msg = f"Evidence requested on '{f.title}': {reason.strip()}"
        audit(a.id, "notification_sent", msg, actor=actor)
        db.session.add(Notification(app_id=a.id, institution_id=a.institution_id,
                                    message=f"[{a.id}] {msg} - please upload updated documents."))
    else:
        recompute_status(a)
    db.session.flush()
    return True, f"Finding updated to {f.state}."


def add_note(a, actor, action, text, token=None):
    if not text.strip():
        return False, "A note is required."
    if token and ReviewAction.query.filter_by(token=token).first():
        return True, "Recorded"
    audit(a.id, action, text.strip()[:200], actor=actor)
    db.session.add(ReviewAction(app_id=a.id, actor=actor, action=action, reason=text.strip(), token=token or None))
    return True, "Recorded."


def set_recommendation(a, actor, choice, note, token=None):
    if choice not in RECOMMENDATIONS:
        return False, "Choose a valid recommendation."
    if token and ReviewAction.query.filter_by(token=token).first():
        return True, "Recorded"
    a.recommendation = choice
    a.recommendation_note = note.strip()
    audit(a.id, "recommendation_recorded", f"{choice}: {note.strip()[:150]}", actor=actor)
    db.session.add(ReviewAction(app_id=a.id, actor=actor, action="recommendation", reason=f"{RECOMMENDATIONS[choice]}: {note or ''}".strip(), token=token or None))
    return True, "Recommendation saved."


def close_in_prototype(a, actor):
    a.status, a.closed_at = "Closed in prototype", datetime.now()
    audit(a.id, "application_closed", "demonstration close", actor=actor)
    db.session.add(ReviewAction(app_id=a.id, actor=actor, action="close", reason="Closed in prototype (demonstration workflow only; not an official decision)"))
    return True, "Closed."


def correct_field(a, field, new_val, reason, actor):
    if not reason.strip():
        return False, "A justification is required for audit."
    if not field.corrected_by:
        field.original_value = field.value
    field.value, field.corrected_by, field.corrected_at = new_val.strip(), actor, datetime.now()
    audit(a.id, "field_corrected", f"{field.document.name}.{field.name}: '{field.original_value}' -> '{field.value}' ({reason.strip()[:150]})", actor=actor)
    db.session.add(ReviewAction(app_id=a.id, actor=actor, action="observation", reason=f"Corrected {field.document.name}.{field.name}: {reason.strip()}"))
    return True, "Field corrected; re-running checks."


# ------------------------------------------------------------------ dashboard KPIs
def _pctl(vals, p):
    if not vals: return None
    vals = sorted(vals); k = min(len(vals) - 1, int(round(p * (len(vals) - 1))))
    return vals[k]


def evaluation_report():
    path = os.path.join(BASE, "data", "eval_report.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def kpis(apps):
    ids = [a.id for a in apps]
    k = {"total": len(apps), "awaiting": sum(a.status in ("Submitted", "Processing") for a in apps)}
    if not ids:
        k.update(review=0, open=0, missing=0, missing_pct=0, pending_ver=0, escalated=0, usable_pct=None, p50=None, p95=None, review_min=None,
                 by_status={}, by_sev={})
        return k
    openF = Finding.query.filter(Finding.app_id.in_(ids), Finding.state.in_(OPEN_STATES)).all()
    allF = Finding.query.filter(Finding.app_id.in_(ids), Finding.state != "resolved").all()
    submitted = [a for a in apps if a.status != "Draft"]
    k["review"] = sum(a.status == "Officer review" for a in apps)
    k["open"] = len(openF)
    miss = {f.app_id for f in allF if f.rule_id.startswith("R-DOC")}
    k["missing"], k["missing_pct"] = len(miss), round(100 * len(miss) / max(len(submitted), 1))
    k["pending_ver"] = sum(f.kind == "verification" and f.rule_id in ("VER-SOURCE_UNAVAILABLE", "VER-MANUAL_REVIEW_REQUIRED", "VER-PENDING") for f in openF)
    k["escalated"] = sum(f.state == "escalated" for f in openF)
    recs = VerificationRecord.query.filter(VerificationRecord.app_id.in_(ids), VerificationRecord.manual == False).all()   # noqa: E712
    k["usable_pct"] = round(100 * sum(r.status in CONCLUSIVE for r in recs) / len(recs)) if recs else None
    runs = ProcessingRun.query.filter(ProcessingRun.app_id.in_(ids), ProcessingRun.status == "done").all()
    ds = [r.duration_s for r in runs if r.duration_s is not None]
    k["p50"] = round(statistics.median(ds), 2) if ds else None
    k["p95"] = round(_pctl(ds, 0.95), 2) if ds else None
    mins = []
    for a in apps:
        first = ProcessingRun.query.filter_by(app_id=a.id, status="done").order_by(ProcessingRun.finished).first()
        acts = ReviewAction.query.filter(ReviewAction.app_id == a.id, ReviewAction.action.in_(list(REVIEW_STATES) + ["close"])).order_by(ReviewAction.ts.desc()).first()
        if first and first.finished and acts:
            mins.append((acts.ts - first.finished).total_seconds() / 60)
    k["review_min"] = round(statistics.mean(mins), 1) if mins else None
    k["by_status"] = dict(Counter(a.status for a in apps))
    k["by_sev"] = dict(Counter(f.severity for f in openF))
    return k
