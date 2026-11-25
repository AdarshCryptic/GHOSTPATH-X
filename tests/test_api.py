"""API tests — full flow through the FastAPI app (apps.api.main:app).

Contract:
  POST /api/v1/labs            -> lab
  GET  /api/v1/labs            -> list labs
  POST /api/v1/scans           -> synchronous; completed scan with
                                  endpoints_discovered=8, identities_mapped=3,
                                  attack_paths=7, validated_findings=3
  GET  /api/v1/scans/{id}      -> scan
  GET  /api/v1/scans/{id}/graph -> node_count > 0, edge_count > 0
  GET  /api/v1/scans/{id}/paths -> 7 paths
  GET  /api/v1/findings        -> exactly 3 validated findings
  GET  /api/v1/findings/{id}   -> one finding
  GET  /api/v1/reports/{id}    -> report

NOTE (backend state, 2026-11-25): ``apps/api/main.py`` exists (207 lines,
created by the backend agent during this test run). Lab creation takes
``{"name", "base_url"}`` (LabCreate schema); reports are keyed by report
id (``rep_*``), which the completed scan record carries as ``report_id``.
"""

from apps.api.main import app  # noqa: F401  (contract import; missing until backend lands)
from conftest import (
    _unwrap,
    create_lab_via_api,
    create_scan_via_api,
    poll_scan_completed,
)

EXPECTED_FINDINGS = {
    "FIND-001": ("Cross-user object authorization", "High"),
    "FIND-002": ("Missing function-level authorization", "High"),
    "FIND-003": ("Invalid workflow transition", "Medium"),
}


def _validated(findings):
    """Findings whose status marks them validated (or that carry no status)."""
    out = []
    for f in findings:
        status = f.get("status", f.get("validation_status", f.get("state")))
        if status is None or str(status).lower() in ("validated", "valid"):
            out.append(f)
    return out


def test_create_lab_and_list_labs(client):
    lab = create_lab_via_api(client)
    assert lab["id"]
    resp = client.get("/api/v1/labs")
    assert resp.status_code == 200
    labs = _unwrap(resp.json(), "labs")
    assert isinstance(labs, list)
    assert any(item.get("id") == lab["id"] for item in labs)


def test_scan_completes_with_expected_counts(client, fresh_lab):
    scan = create_scan_via_api(client, fresh_lab["id"])
    scan = poll_scan_completed(client, scan["id"])
    assert scan["status"] == "completed"
    assert scan["endpoints_discovered"] == 8
    assert scan["identities_mapped"] == 3
    assert scan["attack_paths"] == 7
    assert scan["validated_findings"] == 3


def test_scan_graph_and_paths(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    resp = client.get(f"/api/v1/scans/{scan_id}/graph")
    assert resp.status_code == 200
    graph = _unwrap(resp.json(), "graph")
    assert graph["node_count"] > 0
    assert graph["edge_count"] > 0
    assert graph["node_count"] == len(graph.get("nodes", [])) or "nodes" not in graph
    assert graph["edge_count"] == len(graph.get("edges", [])) or "edges" not in graph

    resp = client.get(f"/api/v1/scans/{scan_id}/paths")
    assert resp.status_code == 200
    payload = resp.json()
    paths = _unwrap(payload, "paths")
    assert isinstance(paths, list)
    assert len(paths) == 7, f"expected 7 attack paths, got {len(paths)}"
    if isinstance(payload, dict) and "count" in payload:
        assert payload["count"] == 7


def test_findings_exactly_three_validated(client, completed_scan):
    resp = client.get("/api/v1/findings")
    assert resp.status_code == 200
    findings = _unwrap(resp.json(), "findings")
    assert isinstance(findings, list)
    validated = _validated(findings)
    assert len(validated) == 3, f"expected 3 validated findings, got {len(validated)}: {findings}"
    by_id = {f["id"]: f for f in validated}
    assert set(by_id) == set(EXPECTED_FINDINGS)
    for finding_id, (title, severity) in EXPECTED_FINDINGS.items():
        assert by_id[finding_id]["title"] == title
        assert by_id[finding_id]["severity"] == severity


def test_finding_by_id_and_report(client, completed_scan):
    scan = completed_scan["scan"]
    scan_id = scan["id"]
    resp = client.get("/api/v1/findings/FIND-001")
    assert resp.status_code == 200
    finding = resp.json()
    assert finding["id"] == "FIND-001"
    assert finding["title"] == "Cross-user object authorization"
    assert finding["severity"] == "High"

    # Reports are keyed by report id (rep_*), not by scan id: the completed
    # scan record carries its report_id.
    report_id = scan.get("report_id")
    assert report_id, f"completed scan must carry report_id, got keys {sorted(scan)}"
    resp = client.get(f"/api/v1/reports/{report_id}")
    assert resp.status_code == 200, f"GET report failed: {resp.status_code} {resp.text[:300]}"
    report = resp.json()
    assert report["scan_id"] == scan_id
    assert report.get("findings"), "report must reference its findings"
    assert "FIND-001" in report["findings"]
