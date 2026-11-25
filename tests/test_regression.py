"""Regression tests — the 8 blueprint scenarios, each its own test.

Scenarios (lab/target.py handle + testing/invariants.py + executor):
  (1) cross-user access detected
  (2) properly protected object -> NO finding (customer_b GET /api/admin/users 403)
  (3) customer admin-only op detected
  (4) admin authorized op -> NO finding
  (5) expired session rejected
  (6) valid workflow transition allowed (created -> paid)
  (7) invalid workflow transition detected (shipped -> created accepted)
  (8) cross-tenant access detected

"No finding" is checked through the real pipeline: run_all_invariants +
build_findings must produce no finding for that endpoint/identity.
"""

from database.store import STORE
from lab.target import handle
from testing.invariants import (
    check_session_boundary,
    check_tenant_isolation,
    check_workflow_integrity,
)
from validation.executor import build_findings, run_all_invariants


def _findings_for_scan(scan_id="scan-regression"):
    results = run_all_invariants(scan_id)
    return build_findings(scan_id, results)


def test_01_cross_user_access_detected():
    resp = handle("customer_b", "GET", "/api/orders/1001")
    assert resp["status"] == 200, f"vuln (a): cross-user read must return 200, got {resp}"
    assert resp["body"]["order"]["id"] == "order_1001"
    assert resp["body"]["order"]["owner"] == "customer_a"


def test_02_protected_object_no_finding():
    resp = handle("customer_b", "GET", "/api/admin/users")
    assert resp["status"] == 403, f"protected object must return 403, got {resp}"
    findings = _findings_for_scan()
    assert not any(f["endpoint"] == "GET /api/admin/users" for f in findings), (
        "a properly protected object must not create a finding"
    )


def test_03_customer_admin_only_op_detected():
    resp = handle("customer_a", "POST", "/api/admin/promote", {"user": "customer_a"})
    assert resp["status"] == 200, f"vuln (b): customer promote must return 200, got {resp}"
    assert resp["body"]["role"] == "admin"


def test_04_admin_authorized_op_no_finding():
    resp = handle("administrator", "POST", "/api/admin/promote", {"user": "customer_a"})
    assert resp["status"] == 200, f"legitimate admin promote must return 200, got {resp}"
    findings = _findings_for_scan()
    assert not any(f.get("identity") == "administrator" for f in findings), (
        "an authorized admin operation must not create a finding"
    )


def test_05_expired_session_rejected():
    resp = handle("customer_a", "GET", "/api/orders/1001", session_valid=False)
    assert resp["status"] == 401, f"expired session must return 401, got {resp}"
    resp = handle("customer_b", "GET", "/api/admin/users", session_valid=False)
    assert resp["status"] == 401
    assert check_session_boundary().outcome == "pass"


def test_06_valid_workflow_transition_allowed():
    # The state model says created -> paid is valid, and the target accepts
    # a valid transition on a real order (order_1002 paid -> shipped).
    from workflows.state_model import is_valid_transition
    from workflows.transition_analyzer import analyze_transition

    assert is_valid_transition("created", "paid") is True
    assert analyze_transition("created", "paid")["expected_status"] == 200
    resp = handle("customer_a", "POST", "/api/orders/1002/transition", {"to_state": "shipped"})
    # order_1002 is owned by customer_b; the transition endpoint does not
    # check ownership, but the (paid -> shipped) pair itself is valid.
    assert resp["status"] == 200, f"valid transition paid->shipped must return 200, got {resp}"
    assert resp["body"]["order"]["state"] == "shipped"


def test_06b_created_order_transition_through_target():
    # BACKEND GAP (see report): POST /api/orders returns 201 with a new
    # order_1003 in state "created", but the order is never persisted in
    # lab.target.ORDERS, so the contract's created -> paid transition
    # cannot be exercised end-to-end through the target (404).
    created = handle("customer_a", "POST", "/api/orders", {"total": 9.99})
    assert created["status"] == 201, f"order creation must return 201, got {created}"
    order_id = created["body"]["order"]["id"]
    assert created["body"]["order"]["state"] == "created"
    resp = handle("customer_a", "POST", f"/api/orders/{order_id}/transition", {"to_state": "paid"})
    assert resp["status"] == 200, (
        f"valid transition created->paid on the just-created order must return 200, "
        f"got {resp} — the created order is not persisted in lab.target.ORDERS"
    )
    assert resp["body"]["order"]["state"] == "paid"


def test_07_invalid_workflow_transition_detected():
    resp = handle("customer_a", "POST", "/api/orders/1001/transition", {"to_state": "created"})
    # Vuln (c): the invalid transition is *accepted* (200) — the flaw the
    # invariant detects (outcome fail), not a rejection.
    assert resp["status"] == 200, f"vuln (c): shipped->created must return 200, got {resp}"
    assert check_workflow_integrity().outcome == "fail"


def test_08_cross_tenant_access_detected():
    resp = handle("customer_a", "GET", "/api/orders/1002")
    assert resp["status"] == 200, f"cross-tenant read must return 200, got {resp}"
    assert resp["body"]["order"]["owner"] == "customer_b"
    assert resp["body"]["order"]["tenant"] == "tenant_b"
    assert check_tenant_isolation().outcome == "fail"


def test_own_order_still_allowed_as_control():
    assert handle("customer_a", "GET", "/api/orders/1001")["status"] == 200
    assert handle("customer_b", "GET", "/api/orders/1002")["status"] == 200
