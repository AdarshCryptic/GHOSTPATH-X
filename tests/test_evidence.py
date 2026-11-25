"""Evidence tests — core/security.py + validation/evidence_capture.py.

Contract: evidence capture redacts password / token / authorization, and
the SHA-256 hash is 64 hex chars and stable for the same input.

All secret values below are fake fixtures (never real credentials).
"""

import hashlib
import json
import re

from core.security import REDACTED, hash_evidence, redact_secrets
from validation.evidence_capture import capture

HEX64 = re.compile(r"^[0-9a-f]{64}$")

FAKE_REQUEST = {
    "identity": "customer_b",
    "method": "GET",
    "path": "/api/orders/1001",
    "headers": {"authorization": "Bearer fake-token-123"},
    "body": {"password": "fake-password-123", "token": "fake-token-abc"},
}
FAKE_RESPONSE = {
    "status": 200,
    "body": {"order": {"id": "order_1001"}},
    "headers": {"authorization": "Bearer fake-response-token"},
}


def test_redacts_password_token_authorization():
    redacted = redact_secrets(FAKE_REQUEST)
    dumped = json.dumps(redacted)
    for secret in ("fake-password-123", "fake-token-abc", "Bearer fake-token-123"):
        assert secret not in dumped, f"secret leaked into redacted evidence: {secret}"
    assert redacted["body"]["password"] == REDACTED
    assert redacted["body"]["token"] == REDACTED
    assert redacted["headers"]["authorization"] == REDACTED
    # Non-sensitive values survive redaction untouched.
    assert redacted["identity"] == "customer_b"
    assert redacted["path"] == "/api/orders/1001"
    assert redacted["method"] == "GET"


def test_redaction_is_recursive_and_case_insensitive():
    data = {"nested": [{"Password": "x", "TOKEN": "y"}], "secret": "z", "keep": "ok"}
    redacted = redact_secrets(data)
    assert redacted["nested"][0]["Password"] == REDACTED
    assert redacted["nested"][0]["TOKEN"] == REDACTED
    assert redacted["secret"] == REDACTED
    assert redacted["keep"] == "ok"


def test_capture_redacts_and_hashes():
    evidence = capture(FAKE_REQUEST, FAKE_RESPONSE)
    dumped = json.dumps(evidence)
    for secret in ("fake-password-123", "fake-token-abc", "fake-response-token"):
        assert secret not in dumped, f"secret leaked into captured evidence: {secret}"
    assert evidence["request"]["body"]["password"] == REDACTED
    assert evidence["response"]["headers"]["authorization"] == REDACTED
    assert HEX64.match(evidence["hash"]), f"hash must be 64 hex chars: {evidence['hash']!r}"


def test_sha256_hash_is_64_hex_and_stable():
    first = hash_evidence(FAKE_REQUEST)
    second = hash_evidence(FAKE_REQUEST)
    assert first == second, "same input must hash identically"
    assert HEX64.match(first), f"hash must be 64 hex chars: {first!r}"
    # Independent recomputation against the documented canonical form.
    canonical = json.dumps(FAKE_REQUEST, sort_keys=True, default=str, separators=(",", ":"))
    assert first == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    # Different input -> different hash; key order must not matter.
    assert hash_evidence({"b": 1, "a": 2}) == hash_evidence({"a": 2, "b": 1})
    assert hash_evidence({"a": 2}) != hash_evidence({"a": 3})


def test_capture_hash_stable_for_same_input():
    assert capture(FAKE_REQUEST, FAKE_RESPONSE)["hash"] == capture(FAKE_REQUEST, FAKE_RESPONSE)["hash"]
