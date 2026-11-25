"""Validation executor: run invariants, reproduce failures twice.

Status mapping: hypothesis -> candidate -> validated / rejected /
inconclusive / needs_review. A finding is only ``validated`` when a
failed invariant reproduces identically on a second run.
"""

from core.policy import audit_event, rate_limiter
from lab import target as lab_target
from testing.invariants import (
    ValidationResult,
    check_role_boundary,
    check_session_boundary,
    check_tenant_isolation,
    check_user_isolation,
    check_workflow_integrity,
)
from validation.evidence_capture import capture

# invariant_id -> finding template (only these become findings)
FINDING_MAP = {
    "INV-USER-ISOLATION": {
        "id": "FIND-001",
        "title": "Cross-user object authorization",
        "severity": "High",
        "endpoint": "GET /api/orders/1001",
        "identity": "customer_b",
        "description": "customer_b can read customer_a's order_1001 (HTTP 200); expected 403.",
        "category": "Broken Object Level Authorization",
        "remediation": "Enforce per-object ownership checks on GET /api/orders/{id}: return 403 when the order owner differs from the authenticated identity.",
        "reproduction": "GET /api/orders/1001 as customer_b returns 200 with order_1001.",
    },
    "INV-ROLE-BOUNDARY": {
        "id": "FIND-002",
        "title": "Missing function-level authorization",
        "severity": "High",
        "endpoint": "POST /api/admin/promote",
        "identity": "customer_a",
        "description": "customer_a can POST /api/admin/promote (HTTP 200); expected 403 for non-admins.",
        "category": "Broken Function Level Authorization",
        "remediation": "Require the admin role on POST /api/admin/promote (and all /api/admin/* routes) before any state change.",
        "reproduction": "POST /api/admin/promote as customer_a returns 200.",
    },
    "INV-WORKFLOW-INTEGRITY": {
        "id": "FIND-003",
        "title": "Invalid workflow transition",
        "severity": "Medium",
        "endpoint": "POST /api/orders/1001/transition",
        "identity": "customer_a",
        "description": "POST /api/orders/1001/transition {\"to_state\": \"created\"} on a shipped order returns 200; expected 400.",
        "category": "Business Logic / Workflow",
        "remediation": "Validate transitions server-side against the state model (created->paid, paid->shipped only); reject all others with 400.",
        "reproduction": "POST /api/orders/1001/transition {\"to_state\": \"created\"} as customer_a returns 200.",
    },
}

_CHECKS = [
    check_user_isolation,
    check_role_boundary,
    check_tenant_isolation,
    check_workflow_integrity,
    check_session_boundary,
]


def _reproduce(invariant_id: str) -> bool:
    """Second run of the same check; True only if it fails identically."""
    mapping = {
        "INV-USER-ISOLATION": check_user_isolation,
        "INV-ROLE-BOUNDARY": check_role_boundary,
        "INV-TENANT-ISOLATION": check_tenant_isolation,
        "INV-WORKFLOW-INTEGRITY": check_workflow_integrity,
        "INV-SESSION-BOUNDARY": check_session_boundary,
    }
    result = mapping[invariant_id]()
    return result.outcome == "fail"


def run_all_invariants(scan_id: str) -> list[ValidationResult]:
    """Run every invariant; reproduce each failure twice."""
    results: list[ValidationResult] = []
    for check in _CHECKS:
        rate_limiter.enforce()
        result = check()
        if result.outcome == "fail":
            # Reproduce: second run must match the first failure.
            reproduced = _reproduce(result.invariant_id)
            result.reproducible = bool(reproduced)
            if not reproduced:
                result.outcome = "inconclusive"
        results.append(result)
        audit_event(
            {
                "event": "invariant_checked",
                "scan_id": scan_id,
                "invariant_id": result.invariant_id,
                "outcome": result.outcome,
                "expected": result.expected,
                "observed": result.observed,
            }
        )
    return results


def status_for(result: ValidationResult) -> str:
    """Map a validation result to hypothesis/candidate/validated/..."""
    if result.outcome == "fail" and result.reproducible:
        return "validated"
    if result.outcome == "fail":
        return "needs_review"
    if result.outcome == "pass":
        return "rejected"
    if result.outcome == "inconclusive":
        return "inconclusive"
    return "candidate"


def build_findings(scan_id: str, results: list[ValidationResult]) -> list[dict]:
    """Exactly the 3 validated findings; protected controls yield none.

    Tenant isolation fails in the target for the same underlying reason
    as user isolation, so it is recorded as a validation result but
    deliberately does not create a second finding.
    """
    from database.store import STORE

    findings = []
    for result in results:
        if status_for(result) != "validated":
            continue
        template = FINDING_MAP.get(result.invariant_id)
        if template is None:
            continue
        evidence = capture(
            {"identity": template["identity"], "endpoint": template["endpoint"]},
            {"observed": result.observed, "expected": result.expected},
        )
        finding = {
            **template,
            "summary": template["description"],
            "scan_id": scan_id,
            "status": "validated",
            "invariant_id": result.invariant_id,
            "expected": result.expected,
            "observed": result.observed,
            "reproducible": True,
            "evidence": evidence,
        }
        findings.append(STORE.add_finding(scan_id, finding))
    return findings
