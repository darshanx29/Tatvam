"""SQLAlchemy models. Stable ids and explicit relations between findings, documents, rule versions and source responses."""
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

INSTITUTION, SCRUTINY, VERIFIER, ADMIN = "institution_admin", "scrutiny_officer", "verification_officer", "system_admin"
OFFICERS = (SCRUTINY, VERIFIER)
ROLE_LABEL = {INSTITUTION: "Institution Administrator", SCRUTINY: "Scrutiny Officer",
              VERIFIER: "Verification Officer", ADMIN: "System Administrator"}
OPEN_STATES = ("open", "escalated", "evidence_requested")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False)
    institution_id = db.Column(db.String(40))
    active = db.Column(db.Boolean, default=True)
    session_epoch = db.Column(db.Integer, default=0)      # bump to revoke every live session of this user


class Application(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    institution_id = db.Column(db.String(40), nullable=False, index=True)
    category = db.Column(db.String(40), default="EoA")
    academic_year = db.Column(db.String(20), default="2026-27")
    programme = db.Column(db.String(120))
    intake = db.Column(db.String(20))
    institution_type = db.Column(db.String(40))
    status = db.Column(db.String(40), default="Draft")
    created_at = db.Column(db.DateTime, default=datetime.now)
    submitted_at = db.Column(db.DateTime)
    last_run = db.Column(db.DateTime)
    report_json = db.Column(db.Text, default="{}")
    recommendation = db.Column(db.String(40))
    recommendation_note = db.Column(db.Text)
    closed_at = db.Column(db.DateTime)

    @property
    def report(self):
        return json.loads(self.report_json or "{}")

    def as_dict(self):
        return {"id": self.id, "institution_id": self.institution_id, "category": self.category,
                "academic_year": self.academic_year, "programme": self.programme, "intake": self.intake,
                "institution_type": self.institution_type, "status": self.status,
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "recommendation": self.recommendation}


class ApplicationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), db.ForeignKey("application.id"), index=True)
    version = db.Column(db.Integer)
    snapshot_json = db.Column(db.Text)
    actor = db.Column(db.String(120))
    reason = db.Column(db.String(60))
    ts = db.Column(db.DateTime, default=datetime.now)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), db.ForeignKey("application.id"), index=True)
    name = db.Column(db.String(200))
    doc_type = db.Column(db.String(40))
    class_conf = db.Column(db.Float)
    ocr_method = db.Column(db.String(30))
    mean_conf = db.Column(db.Float)
    sha = db.Column(db.String(64), index=True)
    phash = db.Column(db.Text)
    size = db.Column(db.Integer)
    signature = db.Column(db.String(30))
    quality_json = db.Column(db.Text)
    qr_json = db.Column(db.Text)
    uploaded_by = db.Column(db.String(120))
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    fields = db.relationship("ExtractedField", backref="document", cascade="all, delete-orphan", order_by="ExtractedField.id")

    @property
    def quality(self):
        return json.loads(self.quality_json) if self.quality_json else None


class ExtractedField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("document.id"), index=True)
    name = db.Column(db.String(60))
    value = db.Column(db.Text)
    confidence = db.Column(db.Float)
    page = db.Column(db.Integer)
    bbox_json = db.Column(db.String(120))
    page_w = db.Column(db.Float)
    page_h = db.Column(db.Float)
    original_value = db.Column(db.Text)       # OCR value before an authorized correction
    corrected_by = db.Column(db.String(120))
    corrected_at = db.Column(db.DateTime)

    @property
    def bbox(self):
        return json.loads(self.bbox_json) if self.bbox_json else None


class VerificationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), index=True)
    doc_name = db.Column(db.String(200))
    basis = db.Column(db.String(300))                  # file hash + verified identifiers at request time
    source = db.Column(db.String(80))
    requested_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(30))                  # verified|mismatch_detected|expired|pending|source_unavailable|manual_review_required
    reference = db.Column(db.String(120))
    detail = db.Column(db.Text)
    attempt = db.Column(db.Integer, default=1)
    manual = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.String(120))

    def as_dict(self):
        return {"document": self.doc_name, "status": self.status, "detail": self.detail, "source": self.source,
                "reference": self.reference, "timestamp": self.requested_at.isoformat(timespec="seconds"),
                "attempt": self.attempt, "manual": bool(self.manual), "verified_by": self.verified_by}


class Finding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), db.ForeignKey("application.id"), index=True)
    kind = db.Column(db.String(20))                    # rule | anomaly | verification | infra
    rule_id = db.Column(db.String(60))
    rule_version = db.Column(db.String(10))
    severity = db.Column(db.String(10))
    title = db.Column(db.String(200))
    source = db.Column(db.String(300))
    observed = db.Column(db.Text)
    expected = db.Column(db.Text)
    reason = db.Column(db.Text)
    next_step = db.Column(db.Text)
    clause = db.Column(db.Text)
    private_detail = db.Column(db.Text)                # officer-only (e.g. which other application holds a duplicate)
    signature = db.Column(db.String(500))
    state = db.Column(db.String(30), default="open")   # open|accepted|dismissed|escalated|evidence_requested

    def as_dict(self, officer=False):
        d = {"id": self.id, "kind": self.kind, "rule_id": self.rule_id, "rule_version": self.rule_version,
             "severity": self.severity, "title": self.title, "source": self.source, "observed": self.observed,
             "expected": self.expected, "reason": self.reason, "next_step": self.next_step, "state": self.state,
             "clause": self.clause}
        if officer:
            d["private_detail"] = self.private_detail
        return d


class ReviewAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("finding.id"), nullable=True)
    app_id = db.Column(db.String(40), index=True)
    actor = db.Column(db.String(120))
    action = db.Column(db.String(30))      # accept|dismiss|escalate|request_evidence|observation|recommendation|close|institution_response
    reason = db.Column(db.Text)
    token = db.Column(db.String(64), unique=True)      # idempotency: a replayed form post is ignored
    ts = db.Column(db.DateTime, default=datetime.now)


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), index=True)      # NULL/"SYSTEM" for admin events
    actor = db.Column(db.String(120))
    event = db.Column(db.String(60))
    detail = db.Column(db.Text)
    ts = db.Column(db.DateTime, default=datetime.now)


class RuleVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(60), index=True)
    version = db.Column(db.String(10))
    definition_json = db.Column(db.Text)
    created_by = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.now)
    note = db.Column(db.String(300))

    @property
    def definition(self):
        return json.loads(self.definition_json)


class Setting(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text)


class ProcessingRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), index=True)
    started = db.Column(db.DateTime, default=datetime.now)
    finished = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="queued")     # queued|running|done|error
    progress = db.Column(db.Integer, default=0)
    message = db.Column(db.String(200))
    duration_s = db.Column(db.Float)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40))
    institution_id = db.Column(db.String(40), index=True)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    read = db.Column(db.Boolean, default=False)
