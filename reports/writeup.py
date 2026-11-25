"""Auto writeup generation (DOCX + PDF) for GHOSTPATH X v0.2.

Open-source only: python-docx for .docx, reportlab for .pdf.
Deterministic filenames under ``reports/``::

    writeup-scan-<scan_id>.docx / .pdf
    writeup-ch-<challenge_id>.docx / .pdf

Generated files are registered on the STORE report record under
``report["writeups"] = {"docx": path, "pdf": path}`` so the download
route can find them.
"""

import html as html_lib
from datetime import datetime, timezone
from pathlib import Path

from core.security import hash_evidence

REPORTS_DIR = Path(__file__).resolve().parent

AUTHOR = "Adarsh"
LAB_NAME = "Juice Shop Training Lab"

_FORMATS = ("docx", "pdf")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _normalise_formats(fmt: str) -> list[str]:
    fmt = (fmt or "").lower()
    if fmt == "both":
        return ["docx", "pdf"]
    if fmt in _FORMATS:
        return [fmt]
    raise ValueError(f"unknown writeup format: {fmt!r} (expected docx, pdf or both)")


# ----------------------------------------------------------------------
# Low-level builders: title + author + sections -> file.
# Sections are [{"heading": str, "body": str | list[str]}].
# ----------------------------------------------------------------------
def build_writeup_docx(title: str, author: str, sections: list[dict], path: str | Path) -> Path:
    from docx import Document

    path = Path(path)
    doc = Document()
    doc.add_heading(title, level=0)
    doc.add_paragraph(f"Author: {author}")
    doc.add_paragraph(f"Generated: {_today()}")
    for section in sections:
        doc.add_heading(section.get("heading", ""), level=1)
        body = section.get("body", "")
        lines = body if isinstance(body, list) else str(body).splitlines()
        for line in lines:
            if line.strip():
                doc.add_paragraph(line)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return path


def build_writeup_pdf(title: str, author: str, sections: list[dict], path: str | Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    path = Path(path)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(html_lib.escape(title), styles["Title"]),
        Paragraph(f"Author: {html_lib.escape(author)}", styles["Normal"]),
        Paragraph(f"Generated: {_today()}", styles["Normal"]),
        Spacer(1, 12),
    ]
    for section in sections:
        story.append(Paragraph(html_lib.escape(section.get("heading", "")), styles["Heading1"]))
        body = section.get("body", "")
        lines = body if isinstance(body, list) else str(body).splitlines()
        for line in lines:
            if line.strip():
                text = html_lib.escape(line).replace("\n", "<br/>")
                story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 6))
    path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=A4, title=title, author=author).build(story)
    return path


_BUILDERS = {"docx": build_writeup_docx, "pdf": build_writeup_pdf}


# ----------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------
def _download_urls(report_id: str, formats: list[str]) -> dict:
    return {
        fmt: f"/api/v1/reports/{report_id}/download?format={fmt}" for fmt in formats
    }


def _build_files(stem: str, title: str, sections: list[dict], formats: list[str]) -> dict:
    """Build the requested files; returns {fmt: Path}."""
    built: dict[str, Path] = {}
    for fmt in formats:
        path = REPORTS_DIR / f"{stem}.{fmt}"
        _BUILDERS[fmt](title, AUTHOR, sections, path)
        built[fmt] = path
    return built


def _register(report: dict, built: dict) -> dict:
    writeups = dict(report.get("writeups") or {})
    for fmt, path in built.items():
        writeups[fmt] = str(path)
    report["writeups"] = writeups
    return report


def _result(report_id: str, formats: list[str], built: dict) -> dict:
    return {
        "report_id": report_id,
        "formats": formats,
        "files": {fmt: Path(built[fmt]).name for fmt in formats},
        "download_urls": _download_urls(report_id, formats),
    }


def _finding_lines(finding: dict) -> list[str]:
    evidence = finding.get("evidence") or {}
    evidence_hash = evidence.get("hash") or hash_evidence(evidence or finding)
    return [
        f"Severity: {finding.get('severity', '')}",
        f"Endpoint: {finding.get('endpoint', '')}",
        f"Identity: {finding.get('identity', '')}",
        f"Description: {finding.get('description', finding.get('summary', ''))}",
        f"Expected: {finding.get('expected', '')}",
        f"Observed: {finding.get('observed', '')}",
        f"Reproduction: {finding.get('reproduction', '')}",
        f"Evidence SHA-256: {evidence_hash}",
        f"Remediation: {finding.get('remediation', '')}",
    ]


# ----------------------------------------------------------------------
# Scan writeups
# ----------------------------------------------------------------------
def generate_scan_writeup(scan_id: str, fmt: str = "both") -> dict:
    """Build a DOCX/PDF writeup for a completed scan."""
    from database.store import STORE

    formats = _normalise_formats(fmt)
    scan = STORE.get_scan(scan_id)
    if scan is None:
        raise ValueError(f"unknown scan: {scan_id}")
    findings = STORE.list_findings(scan_id)

    report = None
    if scan.get("report_id"):
        report = STORE.get_report(scan["report_id"])
    if report is None:
        for candidate in STORE.list_reports():
            if candidate.get("scan_id") == scan_id:
                report = candidate
                break
    if report is None:
        report = STORE.add_report(
            {"scan_id": scan_id, "lab_id": scan.get("lab_id"), "findings": [f.get("id") for f in findings]}
        )

    title = f"GHOSTPATH X — Attack Writeup: Scan {scan_id}"
    sections: list[dict] = [
        {
            "heading": "Scope",
            "body": [
                f"Lab: {scan.get('lab_name', LAB_NAME)}",
                "Environment: isolated lab (explicitly authorized lab only)",
                f"Date: {_today()}",
                f"Scan ID: {scan_id}",
                f"Endpoints discovered: {scan.get('endpoints_discovered', '')}",
                f"Identities mapped: {scan.get('identities_mapped', '')}",
                f"Attack paths: {scan.get('attack_paths', '')}",
                f"Validated findings: {len(findings)}",
            ],
        },
        {
            "heading": "Steps to Reproduce",
            "body": [
                line
                for finding in findings
                for line in [f"{finding.get('id', '')}: {finding.get('reproduction', '')}"]
            ] or ["No validated findings to reproduce."],
        },
    ]
    for finding in findings:
        sections.append(
            {
                "heading": f"{finding.get('id', '')} — {finding.get('title', '')} ({finding.get('severity', '')})",
                "body": _finding_lines(finding),
            }
        )
    sections.append(
        {
            "heading": "Impact",
            "body": [
                f"{f.get('id', '')} ({f.get('severity', '')}): {f.get('description', '')}"
                for f in findings
            ]
            or ["No validated findings — no impact demonstrated."],
        }
    )
    sections.append(
        {
            "heading": "Remediation",
            "body": [
                f"{f.get('id', '')}: {f.get('remediation', '')}" for f in findings
            ]
            or ["No remediation required."],
        }
    )
    sections.append(
        {
            "heading": "Learnings",
            "body": [
                "Authorization must be enforced server-side on every object "
                "and every function — hiding endpoints in the UI is not a control.",
                "Workflow state machines must be validated against the "
                "server-side state model; clients can send any transition.",
                "Every finding above was reproduced deterministically in the "
                "isolated lab and carries a SHA-256 evidence hash.",
            ],
        }
    )

    built = _build_files(f"writeup-scan-{scan_id}", title, sections, formats)
    _register(report, built)
    return _result(report["id"], formats, built)


# ----------------------------------------------------------------------
# Challenge writeups
# ----------------------------------------------------------------------
def generate_challenge_writeup(challenge_id: str, fmt: str = "both", attempt: dict | None = None) -> dict:
    """Build a DOCX/PDF writeup for one challenge.

    Uses the latest recorded attempt for the challenge when ``attempt``
    is not supplied. Creates a STORE report record (scan_id None) when
    none exists for the challenge.
    """
    from challenges.challenges import get_challenge
    from database.store import STORE

    formats = _normalise_formats(fmt)
    challenge = get_challenge(challenge_id)
    if challenge is None:
        raise ValueError(f"unknown challenge: {challenge_id}")

    if attempt is None:
        attempts = STORE.list_challenge_attempts(challenge_id)
        attempt = attempts[-1] if attempts else None

    report = None
    for candidate in STORE.list_reports():
        if candidate.get("challenge_id") == challenge_id:
            report = candidate
            break
    if report is None:
        report = STORE.add_report(
            {"scan_id": None, "challenge_id": challenge_id, "findings": []}
        )

    if attempt is not None:
        evidence = attempt.get("evidence") or {}
        evidence_hash = hash_evidence(attempt)
        reproduce_lines = [
            f"Submitted call: {attempt.get('method', '')} {attempt.get('path', '')} "
            f"as {attempt.get('identity', '')}",
            f"Expected: {evidence.get('expected', '')}",
            f"Observed: {evidence.get('observed', '')}",
            f"Status code: {evidence.get('status_code', '')}",
            f"Result: {attempt.get('status', '')}",
            f"Attempt evidence SHA-256: {evidence_hash}",
        ]
    else:
        reproduce_lines = [
            "No attempt has been recorded for this challenge yet. Solve it "
            "via POST /api/v1/challenges/{id}/solve first, then regenerate "
            "this writeup for real evidence."
        ]

    title = f"GHOSTPATH X — Challenge Writeup: {challenge_id} {challenge['title']}"
    sections: list[dict] = [
        {
            "heading": "Scope",
            "body": [
                f"Lab: {LAB_NAME}",
                "Environment: isolated lab (explicitly authorized lab only)",
                f"Date: {_today()}",
                f"Challenge: {challenge_id} — {challenge['title']}",
                f"Difficulty: {challenge['difficulty']}",
                f"Category: {challenge['category']}",
                f"Attack path: {' -> '.join(challenge['graph_path'])}",
            ],
        },
        {"heading": "Objective", "body": challenge["objective"]},
        {"heading": "Story", "body": challenge["story"]},
        {"heading": "Steps to Reproduce", "body": reproduce_lines},
        {
            "heading": "Impact",
            "body": (
                f"A learner reproducing this challenge demonstrates a real "
                f"{challenge['category']} weakness in the isolated lab: "
                f"{challenge['lesson']}"
            ),
        },
        {"heading": "Remediation", "body": challenge["remediation"]},
        {"heading": "Learnings", "body": challenge["lesson"]},
    ]

    built = _build_files(f"writeup-ch-{challenge_id}", title, sections, formats)
    _register(report, built)
    return _result(report["id"], formats, built)
