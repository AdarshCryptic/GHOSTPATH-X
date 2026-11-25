"""Owner lock tests for GHOSTPATH X v0.4.

The real PIN is never written here. The success test uses a test-only
PIN and computes its SHA-256 hash inside the test with hashlib, then
monkeypatches ``settings.owner_pin_hash`` to that test hash. The only
6-digit literal in this file is that test-only PIN; a test below
asserts no other 6-digit literal exists in this file.
"""

import hashlib
import re
from pathlib import Path

import pytest

from core.config import settings

TEST_PIN = "000000"


def _wrong_pin():
    """A wrong PIN built from the test PIN, never written as a literal."""
    return TEST_PIN[:-1] + "1"


@pytest.fixture(autouse=True)
def _clear_owner_state():
    """Fresh owner sessions + failure counters for every test, so the
    per-IP rate limit from one test never leaks into the next."""
    import apps.api.main as main_mod

    main_mod._owner_sessions.clear()
    main_mod._owner_failures.clear()
    yield
    main_mod._owner_sessions.clear()
    main_mod._owner_failures.clear()


def test_wrong_pin_returns_401(client):
    resp = client.post("/api/v1/owner/unlock", json={"pin": _wrong_pin()})
    assert resp.status_code == 401
    assert resp.json().get("detail") == "incorrect PIN"


def test_malformed_pin_returns_422(client):
    for bad in ("123", "abcdef", "", "12345"):
        resp = client.post("/api/v1/owner/unlock", json={"pin": bad})
        assert resp.status_code == 422, bad
    resp = client.post("/api/v1/owner/unlock", json={"pin": 123})
    assert resp.status_code == 422


def test_five_failures_lock_out_the_sixth_attempt(client):
    wrong = _wrong_pin()
    for _ in range(5):
        resp = client.post("/api/v1/owner/unlock", json={"pin": wrong})
        assert resp.status_code == 401
    resp = client.post("/api/v1/owner/unlock", json={"pin": wrong})
    assert resp.status_code == 429


def test_unlock_and_details_with_test_pin(client, monkeypatch):
    test_hash = hashlib.sha256(TEST_PIN.encode("utf-8")).hexdigest()
    monkeypatch.setattr(settings, "owner_pin_hash", test_hash)
    resp = client.post("/api/v1/owner/unlock", json={"pin": TEST_PIN})
    assert resp.status_code == 200
    token = resp.json().get("token")
    assert isinstance(token, str) and len(token) > 20
    details = client.get(
        "/api/v1/owner/details", headers={"Authorization": f"Bearer {token}"}
    )
    assert details.status_code == 200
    body = details.json()
    assert "Adarsh" in body.get("name", "")
    assert set(body.keys()) == {"name", "role", "title", "projects"}
    assert "@" not in details.text
    assert "GHOSTPATH X" in body.get("role", "")


def test_details_without_token_returns_401(client):
    resp = client.get("/api/v1/owner/details")
    assert resp.status_code == 401
    resp = client.get(
        "/api/v1/owner/details", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


def test_no_other_six_digit_pin_literal_in_this_file():
    text = Path(__file__).read_text(encoding="utf-8")
    found = set(re.findall(r"\b\d{6}\b", text))
    assert found == {TEST_PIN}, f"unexpected 6-digit literals: {found}"
