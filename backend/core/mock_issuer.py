"""Mock issuing-authority adapter.
Preserves existing import interface while delegating to the unified adapter architecture.
"""
import os
from datetime import datetime
from core.adapters import (
    MockIssuerAdapter,
    CONCLUSIVE_STATUSES as CONCLUSIVE,
    STATUS_VERIFIED,
    STATUS_MISMATCH,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_MANUAL_REVIEW,
    STATUS_INCONCLUSIVE,
    parse_date as _parse,
)

REG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_registry.json")
_adapter = MockIssuerAdapter(REG_PATH)


def verify(fields, eval_date, registry=None, attempt=1):
    """Backwards-compatible wrapper delegating to MockIssuerAdapter."""
    res = _adapter.verify(fields, eval_date, attempt=attempt, registry=registry)
    # Ensure backward-compatible dictionary keys
    return {
        "source": res["source"],
        "timestamp": res["timestamp"],
        "reference": res["reference"],
        "attempt": res["attempt"],
        "status": res["status"],
        "detail": res["detail"],
        "is_simulated": res.get("is_simulated", True),
    }
