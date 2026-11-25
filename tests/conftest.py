"""Shared fixtures for GHOSTPATH X v0.2 tests.

Contract under test:
  - FastAPI app at ``apps.api.main:app``
  - In-memory store ``database.store.STORE``
  - Lab target ``lab.target.handle``
  - Tests are deterministic: no network, no sleeps > 1s, no unseeded
    randomness. The store is reset between tests (STORE exposes no
    ``reset()`` method, so the fixture clears its containers directly).
"""

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The test package dir itself, so ``import conftest`` helpers resolve.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

LAB_URL = "http://lab.local"
LAB_NAME = "Juice Shop Training Lab"


@pytest.fixture(autouse=True)
def reset_state():
    """Fresh in-memory store + lab orders + rate limiter for every test."""
    from core.policy import rate_limiter
    from database.store import STORE
    from lab import target as lab_target

    STORE.labs.clear()
    STORE.scans.clear()
    STORE.findings.clear()
    STORE.reports.clear()
    STORE.challenge_attempts.clear()
    STORE.audit.clear()
    STORE._finding_counters.clear()
    lab_target.reset_orders()
    rate_limiter._count = 0
    rate_limiter._window_start = time.monotonic()
    yield
    STORE.labs.clear()
    STORE.scans.clear()
    STORE.findings.clear()
    STORE.reports.clear()
    STORE.challenge_attempts.clear()
    STORE.audit.clear()
    STORE._finding_counters.clear()
    lab_target.reset_orders()


@pytest.fixture
def client():
    """TestClient for the FastAPI app.

    Fails with an exact message (not a suite crash) if the backend agent
    has not created ``apps/api/main.py`` yet.
    """
    try:
        from apps.api.main import app
    except ImportError as exc:  # pragma: no cover - missing backend
        pytest.fail(
            "FastAPI app missing: apps.api.main:app could not be imported "
            f"({exc}). Backend still has to create apps/api/main.py "
            "(run.py already references it)."
        )
    from fastapi.testclient import TestClient

    return TestClient(app)


def _unwrap(payload, *keys):
    """Find a dict/list inside a response payload, tolerating nesting."""
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                return payload[key]
    return payload


def create_lab_via_api(client, name=LAB_NAME, target_url=LAB_URL):
    """Create a lab through the API; tries the contract payload first."""
    payloads = [
        {"name": name, "base_url": target_url},
        {"name": name, "target_url": target_url},
        {"name": name},
        {"target_url": target_url},
    ]
    last = None
    for payload in payloads:
        resp = client.post("/api/v1/labs", json=payload)
        last = resp
        if resp.status_code in (200, 201):
            return resp.json()
    pytest.fail(
        "POST /api/v1/labs did not accept any payload shape; last "
        f"response: {last.status_code} {last.text[:500]}"
    )


def create_scan_via_api(client, lab_id):
    """Create a scan through the API; the contract says it is synchronous."""
    payloads = [
        {"lab_id": lab_id},
        {"lab_id": lab_id, "name": "scan-1"},
    ]
    last = None
    for payload in payloads:
        resp = client.post("/api/v1/scans", json=payload)
        last = resp
        if resp.status_code in (200, 201):
            return resp.json()
    pytest.fail(
        "POST /api/v1/scans did not accept any payload shape; last "
        f"response: {last.status_code} {last.text[:500]}"
    )


def poll_scan_completed(client, scan_id, tries=10, interval=0.2):
    """GET the scan until status == 'completed' (contract: synchronous)."""
    last = None
    for _ in range(tries):
        resp = client.get(f"/api/v1/scans/{scan_id}")
        assert resp.status_code == 200, f"GET scan failed: {resp.status_code} {resp.text[:300]}"
        last = resp.json()
        if _unwrap(last, "scan").get("status") == "completed":
            return _unwrap(last, "scan")
        time.sleep(interval)
    pytest.fail(f"scan {scan_id} never reached 'completed': {last}")


@pytest.fixture
def fresh_lab(client):
    """A lab created through the API."""
    return create_lab_via_api(client)


@pytest.fixture
def completed_scan(client, fresh_lab):
    """A completed scan (synchronous per contract) with its lab."""
    scan = create_scan_via_api(client, fresh_lab["id"])
    scan = poll_scan_completed(client, scan["id"])
    return {"lab": fresh_lab, "scan": scan}
