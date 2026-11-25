"""Redaction and evidence hashing.

No secrets are ever stored. Values under sensitive keys are replaced
with a fixed placeholder before they reach logs, evidence, or reports.
"""

import hashlib
import json
from typing import Any

REDACTED = "***REDACTED***"
_SENSITIVE_KEYS = {"password", "token", "secret", "authorization"}


def redact_secrets(data: Any) -> Any:
    """Recursively redact password/token/secret/authorization values."""
    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                out[key] = REDACTED
            else:
                out[key] = redact_secrets(value)
        return out
    if isinstance(data, list):
        return [redact_secrets(item) for item in data]
    if isinstance(data, tuple):
        return tuple(redact_secrets(item) for item in data)
    return data


def hash_evidence(data: Any) -> str:
    """SHA-256 hex digest of the canonical JSON form of *data*."""
    canonical = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
