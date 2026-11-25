"""Capture redacted HTTP evidence with a SHA-256 hash."""

from core.security import hash_evidence, redact_secrets


def capture(request: dict, response: dict) -> dict:
    """Return a redacted evidence dict with a sha256 hash."""
    evidence = {
        "request": redact_secrets(request),
        "response": redact_secrets(response),
    }
    evidence["hash"] = hash_evidence(evidence)
    return evidence
