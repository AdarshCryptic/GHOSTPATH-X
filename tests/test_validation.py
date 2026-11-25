"""Validation tests — testing/invariants.py + validation/executor.py.

Contract: each invariant returns a ValidationResult with outcome
pass | fail | inconclusive | not_tested.
  - user isolation:      cross-user read succeeds  -> fail
  - role boundary:       customer admin-promote   -> fail
  - tenant isolation:    cross-tenant read        -> fail
  - workflow integrity:  shipped -> created      -> fail
  - session boundary:    expired session -> 401   -> pass (control holds)

Also covers the executor: failures reproduce twice, and exactly the 3
validated findings (FIND-001/002/003) are built — protected controls and
the tenant-isolation duplicate create no extra finding.
"""

from pathlib import Path

from database.store import STORE
from testing.invariants import (
    ALL_INVARIANTS,
    ValidationResult,
    check_role_boundary,
    check_session_boundary,
    check_tenant_isolation,
    check_user_isolation,
    check_workflow_integrity,
)
from validation.executor import build_findings, run_all_invariants, status_for

ALLOWED_OUTCOMES = {"pass", "fail", "inconclusive", "not_tested"}

EXPECTED_FINDINGS = {
    "FIND-001": ("Cross-user object authorization", "High"),
    "FIND-002": ("Missing function-level authorization", "High"),
    "FIND-003": ("Invalid workflow transition", "Medium"),
}


def _assert_result(result, invariant_id):
    assert isinstance(result, ValidationResult)
    assert result.invariant_id == invariant_id
    assert result.outcome in ALLOWED_OUTCOMES, f"outcome {result.outcome!r} not in {ALLOWED_OUTCOMES}"
    assert result.expected, "expected must be non-empty"
    assert result.observed, "observed must be non-empty"


def test_user_isolation_fails_for_cross_user_read():
    result = check_user_isolation()
    _assert_result(result, "INV-USER-ISOLATION")
    assert result.outcome == "fail", f"cross-user read must fail the invariant, got: {result.observed}"
    assert result.reproducible is True


def test_role_boundary_fails_for_customer_admin_promote():
    result = check_role_boundary()
    _assert_result(result, "INV-ROLE-BOUNDARY")
    assert result.outcome == "fail", f"customer promote must fail the invariant, got: {result.observed}"


def test_tenant_isolation_fails_cross_tenant():
    result = check_tenant_isolation()
    _assert_result(result, "INV-TENANT-ISOLATION")
    assert result.outcome == "fail", f"cross-tenant read must fail the invariant, got: {result.observed}"


def test_workflow_integrity_fails_for_shipped_to_created():
    result = check_workflow_integrity()
    _assert_result(result, "INV-WORKFLOW-INTEGRITY")
    assert result.outcome == "fail", f"shipped->created must fail the invariant, got: {result.observed}"


def test_session_boundary_passes_for_expired_session():
    # Expired session returns 401, so the boundary holds -> pass.
    result = check_session_boundary()
    _assert_result(result, "INV-SESSION-BOUNDARY")
    assert result.outcome == "pass", f"expired session must be rejected (401), got: {result.observed}"
    assert "401" in result.observed


def test_all_five_invariants_registered():
    assert {inv.invariant_id for inv in ALL_INVARIANTS} == {
        "INV-USER-ISOLATION",
        "INV-ROLE-BOUNDARY",
        "INV-TENANT-ISOLATION",
        "INV-WORKFLOW-INTEGRITY",
        "INV-SESSION-BOUNDARY",
    }


def test_run_all_invariants_returns_five_results():
    results = run_all_invariants("scan-test")
    assert len(results) == 5
    outcomes = {r.invariant_id: r.outcome for r in results}
    assert outcomes == {
        "INV-USER-ISOLATION": "fail",
        "INV-ROLE-BOUNDARY": "fail",
        "INV-TENANT-ISOLATION": "fail",
        "INV-WORKFLOW-INTEGRITY": "fail",
        "INV-SESSION-BOUNDARY": "pass",
    }
    # Failures reproduced identically on the second run.
    for r in results:
        if r.outcome == "fail":
            assert r.reproducible is True, r.invariant_id
            assert status_for(r) == "validated"
    assert status_for(results[-1]) == "rejected"  # session boundary passed


def test_build_findings_exactly_three_validated():
    results = run_all_invariants("scan-test")
    findings = build_findings("scan-test", results)
    assert len(findings) == 3, f"expected exactly 3 validated findings, got {len(findings)}"
    by_id = {f["id"]: f for f in findings}
    assert set(by_id) == set(EXPECTED_FINDINGS)
    for finding_id, (title, severity) in EXPECTED_FINDINGS.items():
        finding = by_id[finding_id]
        assert finding["title"] == title, f"{finding_id} title mismatch: {finding['title']!r}"
        assert finding["severity"] == severity, f"{finding_id} severity mismatch"
        assert finding["status"] == "validated"
        assert finding["reproducible"] is True
        assert finding["evidence"]["hash"], "finding must carry evidence with a hash"
    # No finding for the protected admin-users control or for tenant isolation.
    endpoints = {f["endpoint"] for f in findings}
    assert "GET /api/admin/users" not in endpoints
    assert not any(f.get("invariant_id") == "INV-TENANT-ISOLATION" for f in findings)


def test_generate_report_for_scan(tmp_path):
    # Exercise reports/generator.py directly (the API layer is missing, so
    # the report endpoint cannot be reached yet — see test_api.py).
    from reports.generator import REPORTS_DIR, generate_report

    scan = STORE.create_scan({"lab_id": "lab-test", "lab_name": "Juice Shop Training Lab"})
    scan_id = scan["id"]
    STORE.update_scan(scan_id, {
        "status": "completed",
        "endpoints_discovered": 8,
        "identities_mapped": 3,
        "attack_paths": 7,
        "validated_findings": 3,
    })
    results = run_all_invariants(scan_id)
    build_findings(scan_id, results)
    json_path = REPORTS_DIR / f"report-{scan_id}.json"
    html_path = REPORTS_DIR / f"report-{scan_id}.html"
    try:
        record = generate_report(scan_id)
        assert record["scan_id"] == scan_id
        assert record["findings"] == ["FIND-001", "FIND-002", "FIND-003"]
        assert json_path.exists() and html_path.exists()
        data = record["data"]
        assert data["counts"] == {
            "endpoints_discovered": 8,
            "identities_mapped": 3,
            "attack_paths": 7,
            "validated_findings": 3,
        }
        assert len(data["findings"]) == 3
        assert "FIND-001" in html_path.read_text(encoding="utf-8")
    finally:
        # The generator writes into reports/; remove test artefacts.
        json_path.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
