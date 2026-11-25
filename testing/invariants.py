"""Authorization / workflow / session invariants.

Every check calls the policy check first, then the simulated target.
Each returns a ValidationResult with expected vs observed.
"""

from dataclasses import dataclass, field

from core.policy import check_url_allowed
from lab import target as lab_target

LAB_URL = "http://127.0.0.1:8000"


@dataclass
class Invariant:
    invariant_id: str
    name: str
    description: str


@dataclass
class ValidationResult:
    invariant_id: str
    outcome: str  # pass | fail | inconclusive | not_tested
    expected: str
    observed: str
    evidence_ids: list[str] = field(default_factory=list)
    reproducible: bool = False


def _policy_ok() -> bool:
    return check_url_allowed(LAB_URL)


def check_user_isolation() -> ValidationResult:
    """customer_b must not read customer_a's order_1001."""
    if not _policy_ok():
        return ValidationResult("INV-USER-ISOLATION", "not_tested", "403 for cross-user order", "policy blocked", [], False)
    resp = lab_target.handle("customer_b", "GET", "/api/orders/1001")
    expected = "403 for cross-user order access"
    observed = f"{resp['status']} for GET /api/orders/1001 as customer_b"
    if resp["status"] == 200:
        return ValidationResult("INV-USER-ISOLATION", "fail", expected, observed, ["ev-user-isolation"], True)
    return ValidationResult("INV-USER-ISOLATION", "pass", expected, observed, ["ev-user-isolation"], False)


def check_role_boundary() -> ValidationResult:
    """customer_a must not be able to POST /api/admin/promote."""
    if not _policy_ok():
        return ValidationResult("INV-ROLE-BOUNDARY", "not_tested", "403 for non-admin promote", "policy blocked", [], False)
    resp = lab_target.handle("customer_a", "POST", "/api/admin/promote", {"user": "customer_a"})
    expected = "403 for non-admin POST /api/admin/promote"
    observed = f"{resp['status']} for POST /api/admin/promote as customer_a"
    if resp["status"] == 200:
        return ValidationResult("INV-ROLE-BOUNDARY", "fail", expected, observed, ["ev-role-boundary"], True)
    return ValidationResult("INV-ROLE-BOUNDARY", "pass", expected, observed, ["ev-role-boundary"], False)


def check_tenant_isolation() -> ValidationResult:
    """customer_a must not read customer_b's order_1002 (tenant_b)."""
    if not _policy_ok():
        return ValidationResult("INV-TENANT-ISOLATION", "not_tested", "403 for cross-tenant order", "policy blocked", [], False)
    resp = lab_target.handle("customer_a", "GET", "/api/orders/1002")
    expected = "403 for cross-tenant order access"
    observed = f"{resp['status']} for GET /api/orders/1002 as customer_a"
    # The lab target's cross-user flaw also exposes cross-tenant orders;
    # it is the same underlying flaw as user isolation, so this check
    # records it as observed but does not create a separate finding.
    if resp["status"] == 200:
        return ValidationResult("INV-TENANT-ISOLATION", "fail", expected, observed, ["ev-tenant-isolation"], True)
    return ValidationResult("INV-TENANT-ISOLATION", "pass", expected, observed, ["ev-tenant-isolation"], False)


def check_workflow_integrity() -> ValidationResult:
    """shipped -> created must be rejected (400)."""
    if not _policy_ok():
        return ValidationResult("INV-WORKFLOW-INTEGRITY", "not_tested", "400 for shipped->created", "policy blocked", [], False)
    resp = lab_target.handle("customer_a", "POST", "/api/orders/1001/transition", {"to_state": "created"})
    expected = "400 for invalid transition shipped -> created"
    observed = f"{resp['status']} for POST /api/orders/1001/transition shipped->created"
    if resp["status"] == 200:
        return ValidationResult("INV-WORKFLOW-INTEGRITY", "fail", expected, observed, ["ev-workflow-integrity"], True)
    return ValidationResult("INV-WORKFLOW-INTEGRITY", "pass", expected, observed, ["ev-workflow-integrity"], False)


def check_session_boundary() -> ValidationResult:
    """Any protected endpoint with session_valid=False must return 401."""
    if not _policy_ok():
        return ValidationResult("INV-SESSION-BOUNDARY", "not_tested", "401 for expired session", "policy blocked", [], False)
    resp = lab_target.handle("customer_b", "GET", "/api/orders/1001", session_valid=False)
    expected = "401 for expired session"
    observed = f"{resp['status']} for GET /api/orders/1001 with expired session"
    if resp["status"] == 401:
        return ValidationResult("INV-SESSION-BOUNDARY", "pass", expected, observed, ["ev-session-boundary"], False)
    return ValidationResult("INV-SESSION-BOUNDARY", "fail", expected, observed, ["ev-session-boundary"], True)


ALL_INVARIANTS = [
    Invariant("INV-USER-ISOLATION", "User isolation", "A user must not access another user's order."),
    Invariant("INV-ROLE-BOUNDARY", "Role boundary", "Only admins may use admin functions."),
    Invariant("INV-TENANT-ISOLATION", "Tenant isolation", "A tenant must not access another tenant's order."),
    Invariant("INV-WORKFLOW-INTEGRITY", "Workflow integrity", "Invalid state transitions must be rejected."),
    Invariant("INV-SESSION-BOUNDARY", "Session boundary", "Expired sessions must be rejected with 401."),
]
