"""Writeup tests — GHOSTPATH X v0.2 DOCX/PDF generation + download."""

import zipfile

from reports.writeup import REPORTS_DIR


def _report_id_for_scan(scan):
    return scan.get("report_id")


def test_scan_writeup_docx_is_valid_zip_with_document_xml(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    resp = client.post(f"/api/v1/scans/{scan_id}/writeup", json={"format": "docx"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scan_id"] == scan_id
    assert payload["formats"] == ["docx"]
    assert payload["files"]["docx"] == f"writeup-scan-{scan_id}.docx"
    path = REPORTS_DIR / payload["files"]["docx"]
    assert path.is_file()
    data = path.read_bytes()
    assert data[:2] == b"PK", "docx must be a zip archive starting with PK"
    with zipfile.ZipFile(path) as zf:
        assert "word/document.xml" in zf.namelist()
        xml = zf.read("word/document.xml").decode("utf-8")
        assert "FIND-001" in xml
        assert "Adarsh" in xml


def test_scan_writeup_pdf_starts_with_pdf_header(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    resp = client.post(f"/api/v1/scans/{scan_id}/writeup", json={"format": "pdf"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["formats"] == ["pdf"]
    path = REPORTS_DIR / payload["files"]["pdf"]
    assert path.is_file()
    data = path.read_bytes()
    assert len(data) > 0
    assert data[:4] == b"%PDF", "pdf must start with %PDF"


def test_scan_writeup_both_registers_on_report(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    report_id = _report_id_for_scan(completed_scan["scan"])
    resp = client.post(f"/api/v1/scans/{scan_id}/writeup", json={"format": "both"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["report_id"] == report_id
    assert set(payload["formats"]) == {"docx", "pdf"}
    report = client.get(f"/api/v1/reports/{report_id}").json()
    assert set(report["writeups"]) == {"docx", "pdf"}
    assert report["writeups"]["docx"].endswith(f"writeup-scan-{scan_id}.docx")


def test_download_route_content_types(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    report_id = _report_id_for_scan(completed_scan["scan"])
    client.post(f"/api/v1/scans/{scan_id}/writeup", json={"format": "both"})

    resp = client.get(f"/api/v1/reports/{report_id}/download?format=docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert resp.content[:2] == b"PK"

    resp = client.get(f"/api/v1/reports/{report_id}/download?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"


def test_download_route_404s(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    report_id = _report_id_for_scan(completed_scan["scan"])
    # No writeup generated yet for this report in this test (fresh store).
    resp = client.get(f"/api/v1/reports/{report_id}/download?format=docx")
    assert resp.status_code == 404
    resp = client.get("/api/v1/reports/rep_doesnotexist/download?format=docx")
    assert resp.status_code == 404
    resp = client.get(f"/api/v1/reports/{report_id}/download?format=txt")
    assert resp.status_code == 422
    resp = client.post(f"/api/v1/scans/scan_doesnotexist/writeup", json={"format": "docx"})
    assert resp.status_code == 404


def test_email_route_validation_and_fallback(client, completed_scan):
    scan_id = completed_scan["scan"]["id"]
    report_id = _report_id_for_scan(completed_scan["scan"])
    # Invalid / empty email -> 422, and no writeup is generated.
    resp = client.post(
        f"/api/v1/reports/{report_id}/email", json={"email": "not-an-email", "format": "docx"}
    )
    assert resp.status_code == 422
    resp = client.post(
        f"/api/v1/reports/{report_id}/email", json={"email": "", "format": "docx"}
    )
    assert resp.status_code == 422
    # Unknown report -> 404.
    resp = client.post(
        "/api/v1/reports/rep_doesnotexist/email",
        json={"email": "a@example.com", "format": "docx"},
    )
    assert resp.status_code == 404
    # Valid email: reports/email.py is not present yet, so the route falls
    # back gracefully to a locally queued result (verbatim shape).
    resp = client.post(
        f"/api/v1/reports/{report_id}/email", json={"email": "a@example.com", "format": "both"}
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] in ("queued_locally", "sent")
    assert payload["email"] == "a@example.com"
    assert payload["report_id"] == report_id
    assert "download_urls" in payload
    assert "mailto" in payload
    # The email call generated the writeup files first.
    assert (REPORTS_DIR / f"writeup-scan-{scan_id}.docx").is_file()
    assert (REPORTS_DIR / f"writeup-scan-{scan_id}.pdf").is_file()


def test_main_scan_counts_unchanged(client, completed_scan):
    """v0.1 regression guard: the live scan still yields 8/3/7/3."""
    scan = completed_scan["scan"]
    assert scan["status"] == "completed"
    assert scan["endpoints_discovered"] == 8
    assert scan["identities_mapped"] == 3
    assert scan["attack_paths"] == 7
    assert scan["validated_findings"] == 3

    resp = client.get(f"/api/v1/scans/{scan['id']}/graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert graph["node_count"] == 19
    assert graph["edge_count"] == 24

    resp = client.get("/api/v1/findings")
    assert len(resp.json()) == 3
