"""Report generator: JSON + HTML (inline template, no external assets)."""

import html as html_lib
import json
from pathlib import Path

from database.store import STORE

REPORTS_DIR = Path(__file__).resolve().parent


def generate_report(scan_id: str) -> dict:
    scan = STORE.get_scan(scan_id)
    if scan is None:
        raise ValueError(f"unknown scan: {scan_id}")
    findings = STORE.list_findings(scan_id)
    # Counts are derived from the actual pipeline artefacts, not from the
    # scan record snapshot: the report is generated before the pipeline's
    # final update_scan, so the snapshot still says running / 0.
    from discovery.api_inventory import get_inventory
    from graph.builder import SecurityGraph
    from identity.role_registry import get_identities

    report_data = {
        "scan_id": scan_id,
        "lab_id": scan.get("lab_id"),
        "lab_name": scan.get("lab_name", "Juice Shop Training Lab"),
        "status": "completed",
        "counts": {
            "endpoints_discovered": len(get_inventory()),
            "identities_mapped": len(get_identities()),
            "attack_paths": len(SecurityGraph(scan_id=scan_id).build_lab_graph().candidate_paths()),
            "validated_findings": len(findings),
        },
        "findings": findings,
    }
    json_path = REPORTS_DIR / f"report-{scan_id}.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html_lib.escape(f.get("id", "")),
            html_lib.escape(f.get("title", "")),
            html_lib.escape(f.get("severity", "")),
            html_lib.escape(f.get("endpoint", "")),
            html_lib.escape(f.get("observed", "")),
            html_lib.escape(f.get("remediation", "")),
        )
        for f in findings
    )
    html_doc = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>GHOSTPATH X — Report {scan_id}</title>
<style>body{{font-family:sans-serif;margin:2rem}}table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:6px 10px;text-align:left}}</style>
</head><body>
<h1>GHOSTPATH X — Scan Report</h1>
<p>Author: Adarsh</p>
<p>Scan: {scan_id} &nbsp; Lab: {lab}</p>
<p>Endpoints: {ep} &nbsp; Identities: {ident} &nbsp; Attack paths: {paths} &nbsp; Validated findings: {findings_n}</p>
<table><tr><th>ID</th><th>Title</th><th>Severity</th><th>Endpoint</th><th>Observed</th><th>Remediation</th></tr>
{rows}
</table>
<footer><p>Built by Adarsh &bull; GHOSTPATH X v0.2</p></footer>
</body></html>""".format(
        scan_id=html_lib.escape(scan_id),
        lab=html_lib.escape(str(report_data["lab_name"])),
        ep=report_data["counts"]["endpoints_discovered"],
        ident=report_data["counts"]["identities_mapped"],
        paths=report_data["counts"]["attack_paths"],
        findings_n=report_data["counts"]["validated_findings"],
        rows=rows,
    )
    html_path = REPORTS_DIR / f"report-{scan_id}.html"
    html_path.write_text(html_doc, encoding="utf-8")

    record = STORE.add_report(
        {
            "scan_id": scan_id,
            "lab_id": scan.get("lab_id"),
            "findings": [f.get("id") for f in findings],
            "json_path": str(json_path),
            "html_path": str(html_path),
            "data": report_data,
        }
    )
    return record
