"""Verification Adapter Architecture.
Provides a unified interface for issuing-authority verification adapters:
- MockIssuerAdapter (simulated registry)
- ManualReviewAdapter (authorized officer verification)
- DigitalSignatureAdapter (cryptographic signature status)
- QRCodeVerificationAdapter (allow-listed official QR verification)

Standard verification statuses:
- VERIFIED
- MISMATCH_DETECTED
- EXPIRED
- PENDING
- SOURCE_UNAVAILABLE
- MANUAL_REVIEW_REQUIRED
- INCONCLUSIVE
"""
import abc
import json
import os
from datetime import datetime, date
from typing import Dict, Any, Optional

STATUS_VERIFIED = "verified"
STATUS_MISMATCH = "mismatch_detected"
STATUS_EXPIRED = "expired"
STATUS_PENDING = "pending"
STATUS_SOURCE_UNAVAILABLE = "source_unavailable"
STATUS_MANUAL_REVIEW = "manual_review_required"
STATUS_INCONCLUSIVE = "inconclusive"

ALL_STATUSES = (
    STATUS_VERIFIED,
    STATUS_MISMATCH,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_MANUAL_REVIEW,
    STATUS_INCONCLUSIVE,
)

CONCLUSIVE_STATUSES = (STATUS_VERIFIED, STATUS_MISMATCH, STATUS_EXPIRED)


def parse_date(d_str: str) -> Optional[date]:
    """Parse dd-mm-yyyy or dd/mm/yyyy into date object."""
    try:
        return datetime.strptime(str(d_str).replace("/", "-"), "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None


class BaseVerificationAdapter(abc.ABC):
    """Abstract base class for all verification adapters."""

    adapter_name: str = "BASE"
    is_simulated: bool = True

    @abc.abstractmethod
    def verify(
        self,
        fields: Dict[str, Any],
        eval_date: datetime,
        attempt: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform verification against source or simulation.
        Returns normalized dictionary with:
        - status: one of ALL_STATUSES
        - source: human-readable source label
        - reference: extracted identifier/certificate number
        - detail: human-readable explanation
        - timestamp: ISO 8601 string
        - attempt: int attempt count
        - is_simulated: bool
        """
        pass


class MockIssuerAdapter(BaseVerificationAdapter):
    """Mock issuing-authority registry adapter (SIMULATION).
    Used for local development, automated testing, and SIH demonstrations.
    Special reference prefixes for testing:
    - UNAVAIL*: always unreachable
    - FLAKY*: unreachable on attempt 1, resolves on attempt 2
    - PENDING*: pending response
    """

    adapter_name = "MOCK-ISSUER-REGISTRY"
    is_simulated = True

    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = registry_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "mock_registry.json"
        )
        self._cached_registry = None

    def _load_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def verify(
        self,
        fields: Dict[str, Any],
        eval_date: datetime,
        attempt: int = 1,
        registry: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        reg = registry if registry is not None else self._load_registry()
        ts = datetime.now().isoformat(timespec="seconds")
        ref = (fields.get("certificate_no") or {}).get("value")
        eval_d = eval_date.date() if isinstance(eval_date, datetime) else eval_date

        base = {
            "source": self.adapter_name,
            "timestamp": ts,
            "reference": ref,
            "attempt": attempt,
            "is_simulated": True,
        }

        if not ref:
            return {
                **base,
                "status": STATUS_MANUAL_REVIEW,
                "detail": "No reference number extracted; route to manual scrutiny",
            }

        # Simulated operational hooks for testing resilience:
        if ref.startswith("UNAVAIL") or (ref.startswith("FLAKY") and attempt < 2):
            return {
                **base,
                "status": STATUS_SOURCE_UNAVAILABLE,
                "detail": "Simulated issuer registry connection timeout (source unavailable)",
            }

        if ref.startswith("PENDING"):
            return {
                **base,
                "status": STATUS_PENDING,
                "detail": "Simulated external check in progress (pending response)",
            }

        rec = reg.get(ref)
        if not rec:
            return {
                **base,
                "status": STATUS_MANUAL_REVIEW,
                "detail": "Reference not found in mock issuer registry; manual review required",
            }

        diffs = []
        iid = (fields.get("institution_id") or {}).get("value")
        if iid and rec.get("institution_id") and iid != rec["institution_id"]:
            diffs.append(f"institution_id: submitted {iid} vs source {rec['institution_id']}")

        vu = (fields.get("valid_until") or {}).get("value")
        if vu and rec.get("valid_until") and vu != rec["valid_until"]:
            diffs.append(f"valid_until: submitted {vu} vs source {rec['valid_until']}")

        if diffs:
            return {
                **base,
                "status": STATUS_MISMATCH,
                "detail": "; ".join(diffs),
            }

        valid_until_date = parse_date(rec.get("valid_until", ""))
        if valid_until_date and valid_until_date < eval_d:
            return {
                **base,
                "status": STATUS_EXPIRED,
                "detail": f"Source records indicate certificate expired on {rec['valid_until']}",
            }

        return {
            **base,
            "status": STATUS_VERIFIED,
            "detail": "Source registry confirms record and field alignment",
        }


class ManualVerificationAdapter(BaseVerificationAdapter):
    """Authorized manual review verification adapter."""

    adapter_name = "MANUAL-REVIEW"
    is_simulated = False

    def verify(
        self,
        fields: Dict[str, Any],
        eval_date: datetime,
        attempt: int = 1,
        officer: str = "officer",
        outcome: str = STATUS_VERIFIED,
        note: str = "",
        reference: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        ts = datetime.now().isoformat(timespec="seconds")
        ref = reference or (fields.get("certificate_no") or {}).get("value")
        return {
            "source": f"MANUAL ({officer})",
            "timestamp": ts,
            "reference": ref,
            "status": outcome if outcome in ALL_STATUSES else STATUS_MANUAL_REVIEW,
            "detail": note or "Manual review outcome recorded by authorized officer",
            "attempt": attempt,
            "is_simulated": False,
            "verified_by": officer,
        }


class VerificationRegistry:
    """Registry managing available verification adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseVerificationAdapter] = {
            "mock": MockIssuerAdapter(),
            "manual": ManualVerificationAdapter(),
        }

    def register(self, key: str, adapter: BaseVerificationAdapter):
        self._adapters[key] = adapter

    def get(self, key: str = "mock") -> BaseVerificationAdapter:
        return self._adapters.get(key, self._adapters["mock"])


# Default global adapter registry
default_registry = VerificationRegistry()
