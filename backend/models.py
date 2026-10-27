"""SQLAlchemy models. Stable ids and explicit relations between findings, documents, rule versions and source responses."""
import json
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session, backref

BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE, "smartverify.db"))

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

Base = declarative_base()
Base.query = db_session.query_property()


def migrate_schema():
    """Ensure all declared columns exist in existing database tables (preserves existing data)."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        with engine.connect() as conn:
            for table_name, table in Base.metadata.tables.items():
                if inspector.has_table(table_name):
                    existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                    for col in table.columns:
                        if col.name not in existing_cols:
                            col_type = col.type.compile(engine.dialect)
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))
                            conn.commit()
    except Exception:
        pass


class _DBProxy:
    def __init__(self):
        self.session = db_session
        self.Model = Base
        self.Column = Column
        self.Integer = Integer
        self.String = String
        self.Boolean = Boolean
        self.Float = Float
        self.Text = Text
        self.DateTime = DateTime
        self.ForeignKey = ForeignKey
        self.relationship = relationship
        self.backref = backref

    def create_all(self):
        Base.metadata.create_all(bind=engine)
        migrate_schema()

    def drop_all(self):
        Base.metadata.drop_all(bind=engine)



db = _DBProxy()

INSTITUTION, SCRUTINY, VERIFIER, ADMIN = "institution_admin", "scrutiny_officer", "verification_officer", "system_admin"
OFFICERS = (SCRUTINY, VERIFIER)
ROLE_LABEL = {
    INSTITUTION: "Institution Administrator",
    SCRUTINY: "Scrutiny Officer",
    VERIFIER: "Verification Officer",
    ADMIN: "System Administrator"
}
OPEN_STATES = ("open", "escalated", "evidence_requested")


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    name = Column(String(120))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(40), nullable=False)
    institution_id = Column(String(40))
    active = Column(Boolean, default=True)
    session_epoch = Column(Integer, default=0)      # bump to revoke every live session of this user


class Application(Base):
    __tablename__ = "application"

    id = Column(String(40), primary_key=True)
    institution_id = Column(String(40), nullable=False, index=True)
    category = Column(String(40), default="EoA")
    academic_year = Column(String(20), default="2026-27")
    programme = Column(String(120))
    intake = Column(String(20))
    institution_type = Column(String(40))
    status = Column(String(40), default="Draft")
    created_at = Column(DateTime, default=datetime.now)
    submitted_at = Column(DateTime)
    last_run = Column(DateTime)
    report_json = Column(Text, default="{}")
    recommendation = Column(String(40))
    recommendation_note = Column(Text)
    closed_at = Column(DateTime)

    @property
    def report(self):
        return json.loads(self.report_json or "{}")

    def as_dict(self):
        return {
            "id": self.id,
            "institution_id": self.institution_id,
            "category": self.category,
            "academic_year": self.academic_year,
            "programme": self.programme,
            "intake": self.intake,
            "institution_type": self.institution_type,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "recommendation": self.recommendation
        }


class ApplicationVersion(Base):
    __tablename__ = "application_version"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), ForeignKey("application.id"), index=True)
    version = Column(Integer)
    snapshot_json = Column(Text)
    actor = Column(String(120))
    reason = Column(String(60))
    ts = Column(DateTime, default=datetime.now)


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), ForeignKey("application.id"), index=True)
    name = Column(String(200))
    doc_type = Column(String(40))
    class_conf = Column(Float)
    ocr_method = Column(String(30))
    mean_conf = Column(Float)
    sha = Column(String(64), index=True)
    phash = Column(Text)
    size = Column(Integer)
    signature = Column(String(30))
    quality_json = Column(Text)
    qr_json = Column(Text)
    uploaded_by = Column(String(120))
    uploaded_at = Column(DateTime, default=datetime.now)
    fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan", order_by="ExtractedField.id")

    @property
    def quality(self):
        return json.loads(self.quality_json) if self.quality_json else None


class ExtractedField(Base):
    __tablename__ = "extracted_field"

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey("document.id"), index=True)
    name = Column(String(60))
    value = Column(Text)
    confidence = Column(Float)
    page = Column(Integer)
    bbox_json = Column(String(120))
    page_w = Column(Float)
    page_h = Column(Float)
    original_value = Column(Text)       # OCR value before an authorized correction
    corrected_by = Column(String(120))
    corrected_at = Column(DateTime)
    document = relationship("Document", back_populates="fields")

    @property
    def bbox(self):
        return json.loads(self.bbox_json) if self.bbox_json else None


class VerificationRecord(Base):
    __tablename__ = "verification_record"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), index=True)
    doc_name = Column(String(200))
    basis = Column(String(300))                  # file hash + verified identifiers at request time
    source = Column(String(80))
    requested_at = Column(DateTime, default=datetime.now)
    status = Column(String(30))                  # verified|mismatch_detected|expired|pending|source_unavailable|manual_review_required
    reference = Column(String(120))
    detail = Column(Text)
    attempt = Column(Integer, default=1)
    manual = Column(Boolean, default=False)
    verified_by = Column(String(120))

    def as_dict(self):
        return {
            "document": self.doc_name,
            "status": self.status,
            "detail": self.detail,
            "source": self.source,
            "reference": self.reference,
            "timestamp": self.requested_at.isoformat(timespec="seconds") if self.requested_at else None,
            "attempt": self.attempt,
            "manual": bool(self.manual),
            "verified_by": self.verified_by
        }


class Finding(Base):
    __tablename__ = "finding"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), ForeignKey("application.id"), index=True)
    kind = Column(String(20))                    # rule | anomaly | verification | infra
    rule_id = Column(String(60))
    rule_version = Column(String(10))
    severity = Column(String(10))
    title = Column(String(200))
    source = Column(String(300))
    observed = Column(Text)
    expected = Column(Text)
    reason = Column(Text)
    next_step = Column(Text)
    clause = Column(Text)
    private_detail = Column(Text)                # officer-only (e.g. which other application holds a duplicate)
    signature = Column(String(500))
    state = Column(String(30), default="open")   # open|accepted|dismissed|escalated|evidence_requested

    def as_dict(self, officer=False):
        d = {
            "id": self.id,
            "kind": self.kind,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "severity": self.severity,
            "title": self.title,
            "source": self.source,
            "observed": self.observed,
            "expected": self.expected,
            "reason": self.reason,
            "next_step": self.next_step,
            "state": self.state,
            "clause": self.clause
        }
        if officer:
            d["private_detail"] = self.private_detail
        return d


class ReviewAction(Base):
    __tablename__ = "review_action"

    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("finding.id"), nullable=True)
    app_id = Column(String(40), index=True)
    actor = Column(String(120))
    action = Column(String(30))      # accept|dismiss|escalate|request_evidence|observation|recommendation|close|institution_response
    reason = Column(Text)
    token = Column(String(64), unique=True)      # idempotency: a replayed form post is ignored
    ts = Column(DateTime, default=datetime.now)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), index=True)      # NULL/"SYSTEM" for admin events
    actor = Column(String(120))
    event = Column(String(60))
    detail = Column(Text)
    ts = Column(DateTime, default=datetime.now)
    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=True)


class RuleVersion(Base):
    __tablename__ = "rule_version"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String(60), index=True)
    version = Column(String(10))
    definition_json = Column(Text)
    created_by = Column(String(120))
    created_at = Column(DateTime, default=datetime.now)
    note = Column(String(300))

    @property
    def definition(self):
        return json.loads(self.definition_json)


class Setting(Base):
    __tablename__ = "setting"

    key = Column(String(60), primary_key=True)
    value = Column(Text)


class ProcessingRun(Base):
    __tablename__ = "processing_run"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40), index=True)
    started = Column(DateTime, default=datetime.now)
    finished = Column(DateTime)
    status = Column(String(20), default="queued")     # queued|running|done|error
    progress = Column(Integer, default=0)
    message = Column(String(200))
    duration_s = Column(Float)


class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(40))
    institution_id = Column(String(40), index=True)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    read = Column(Boolean, default=False)
