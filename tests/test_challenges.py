"""Challenge tests — GHOSTPATH X v0.2 challenges + solve endpoint."""

import pytest

from database.store import STORE
from lab.target import handle

REQUIRED_FIELDS = {
    "id",
    "title",
    "difficulty",
    "category",
    "story",
    "objective",
    "hints",
    "lesson",
    "remediation",
    "graph_path",
}


def test_list_challenges_returns_six_with_required_fields(client):
    resp = client.get("/api/v1/challenges")
    assert resp.status_code == 200
    challenges = resp.json()
    assert isinstance(challenges, list)
    assert len(challenges) == 6, f"expected 6 challenges, got {len(challenges)}"
    ids = [c["id"] for c in challenges]
    assert ids == ["CH-01", "CH-02", "CH-03", "CH-04", "CH-05", "CH-06"]
    for challenge in challenges:
        assert REQUIRED_FIELDS <= set(challenge), f"{challenge['id']} missing fields"
        assert isinstance(challenge["hints"], list) and len(challenge["hints"]) == 3, (
            f"{challenge['id']} must have exactly 3 hints"
        )
        assert challenge["difficulty"] in ("Easy", "Medium", "Hard")
        assert challenge["graph_path"], f"{challenge['id']} needs a graph_path"
        assert challenge["download_url"] == f"/api/v1/challenges/{challenge['id']}/brief"


def test_get_one_challenge_and_404(client):
    resp = client.get("/api/v1/challenges/CH-03")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Invalid Workflow Transition"
    assert resp.json()["difficulty"] == "Medium"
    resp = client.get("/api/v1/challenges/CH-99")
    assert resp.status_code == 404


def test_brief_download_has_attachment_header_and_content(client):
    resp = client.get("/api/v1/challenges/CH-01/brief")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert 'filename="ch-01-brief.md"' in resp.headers["content-disposition"]
    body = resp.text
    assert "Cross-User Order Access" in body
    assert "## Objective" in body
    assert "## Hints" in body
    assert "Easy" in body
    assert "## Story" in body
    resp = client.get("/api/v1/challenges/CH-99/brief")
    assert resp.status_code == 404


def _solve(client, challenge_id, payload):
    return client.post(f"/api/v1/challenges/{challenge_id}/solve", json=payload)


def test_solve_ch01_correct_call_solved(client):
    resp = _solve(
        client,
        "CH-01",
        {"identity": "customer_b", "method": "GET", "path": "/api/orders/1001"},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["challenge_id"] == "CH-01"
    assert result["solved"] is True
    assert result["status"] == "solved"
    assert result["evidence"]["status_code"] == 200
    assert "200" in result["evidence"]["observed"]
    # The attempt is recorded in the store.
    assert len(STORE.list_challenge_attempts("CH-01")) == 1


def test_solve_ch01_wrong_identity_and_wrong_action_fail(client):
    # Wrong identity: customer_a owns order_1001, so this is not the vuln.
    resp = _solve(
        client,
        "CH-01",
        {"identity": "customer_a", "method": "GET", "path": "/api/orders/1001"},
    )
    assert resp.status_code == 200
    assert resp.json()["solved"] is False
    assert resp.json()["status"] == "failed"

    # Wrong action: a protected endpoint that correctly returns 403.
    resp = _solve(
        client,
        "CH-01",
        {"identity": "customer_b", "method": "GET", "path": "/api/admin/users"},
    )
    assert resp.status_code == 200
    assert resp.json()["solved"] is False

    # Unknown identity / malformed action shape -> 422.
    resp = _solve(
        client,
        "CH-01",
        {"identity": "mallory", "method": "GET", "path": "/api/orders/1001"},
    )
    assert resp.status_code == 422
    resp = _solve(client, "CH-01", {"identity": "customer_b", "method": "GET", "path": "orders"})
    assert resp.status_code == 422
    resp = _solve(client, "CH-99", {"identity": "customer_b", "method": "GET", "path": "/api/orders/1001"})
    assert resp.status_code == 404


def test_solve_ch02_ch03_ch05(client):
    resp = _solve(
        client,
        "CH-02",
        {"identity": "customer_a", "method": "POST", "path": "/api/admin/promote",
         "body": {"user": "customer_a"}},
    )
    assert resp.json()["solved"] is True

    resp = _solve(
        client,
        "CH-03",
        {"identity": "customer_a", "method": "POST", "path": "/api/orders/1001/transition",
         "body": {"to_state": "created"}},
    )
    assert resp.json()["solved"] is True
    # A *valid* transition body must not solve CH-03.
    resp = _solve(
        client,
        "CH-03",
        {"identity": "customer_a", "method": "POST", "path": "/api/orders/1001/transition",
         "body": {"to_state": "paid"}},
    )
    assert resp.json()["solved"] is False

    resp = _solve(
        client,
        "CH-05",
        {"identity": "customer_a", "method": "GET", "path": "/api/orders/1002"},
    )
    assert resp.json()["solved"] is True


def test_solve_ch04_expired_session_solved_when_401_observed(client):
    # The control works: an expired session must be rejected with 401,
    # and observing that rejection IS the solve.
    resp = _solve(
        client,
        "CH-04",
        {"identity": "customer_b", "method": "GET", "path": "/api/orders/1001",
         "session_valid": False},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["solved"] is True
    assert result["evidence"]["status_code"] == 401
    assert "401" in result["evidence"]["observed"]
    assert "rejected" in result["message"].lower() or "401" in result["message"]

    # A valid session is not the challenge: 200 here must NOT solve CH-04.
    resp = _solve(
        client,
        "CH-04",
        {"identity": "customer_b", "method": "GET", "path": "/api/orders/1001",
         "session_valid": True},
    )
    assert resp.json()["solved"] is False


def test_solve_ch06_price_tamper(client):
    resp = _solve(
        client,
        "CH-06",
        {"identity": "customer_b", "method": "POST", "path": "/api/orders/1001/total",
         "body": {"total": 0.01}},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["solved"] is True
    assert result["evidence"]["status_code"] == 200
    assert "0.01" in result["evidence"]["observed"]

    # The tamper must not persist: the stored order still totals 49.99.
    assert handle("customer_a", "GET", "/api/orders/1001")["body"]["order"]["total"] == 49.99
    # A different total does not solve the challenge.
    resp = _solve(
        client,
        "CH-06",
        {"identity": "customer_b", "method": "POST", "path": "/api/orders/1001/total",
         "body": {"total": 9.99}},
    )
    assert resp.json()["solved"] is False


def test_challenge_writeup_route(client):
    _solve(
        client,
        "CH-01",
        {"identity": "customer_b", "method": "GET", "path": "/api/orders/1001"},
    )
    resp = client.post("/api/v1/challenges/CH-01/writeup", json={"format": "both"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["challenge_id"] == "CH-01"
    assert payload["formats"] == ["docx", "pdf"]
    assert set(payload["files"]) == {"docx", "pdf"}
    assert payload["report_id"].startswith("rep_")
    assert payload["download_urls"]["docx"].endswith("?format=docx")
    resp = client.post("/api/v1/challenges/CH-99/writeup", json={"format": "docx"})
    assert resp.status_code == 404
    resp = client.post("/api/v1/challenges/CH-01/writeup", json={"format": "txt"})
    assert resp.status_code == 422
