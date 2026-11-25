"""Tests for reports/email.py — GHOSTPATH X v0.2 email box.

Contract under test (route owned by another agent; this file only tests
that the route calls ``reports.email.send_or_queue`` per the shared spec):
  POST /api/v1/reports/{report_id}/email  with JSON
  {"email": "<address>", "format": "docx" | "pdf" | "both"}
    -> invalid email: 422
    -> valid email, no SMTP env: 200, {"status": "queued_locally", ...}
       with download_urls + mailto, and a record in reports/outbox.json
    -> valid email, SMTP configured: 200, {"status": "sent", ...}

If the route does not exist yet, the API tests fail with an explicit
BLOCKER message naming the missing route (they do not invent it).

The outbox path is monkeypatched to a tmp dir for every test in this
file, so no test record ever lands in the real reports/outbox.json.
Unit tests call send_or_queue directly with monkeypatched env vars.
"""

import json
import smtplib
from pathlib import Path

import pytest

import reports.email as email_mod
from reports.email import send_or_queue

SMTP_ENV_VARS = [
    "GHOSTPATH_SMTP_HOST",
    "GHOSTPATH_SMTP_PORT",
    "GHOSTPATH_SMTP_USER",
    "GHOSTPATH_SMTP_PASS",
    "GHOSTPATH_SMTP_FROM",
]


@pytest.fixture(autouse=True)
def _isolated_outbox_and_env(monkeypatch, tmp_path):
    """No SMTP env vars; outbox redirected to a tmp file for this test."""
    for var in SMTP_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(email_mod, "OUTBOX_PATH", tmp_path / "outbox.json")
    yield


def _read_outbox():
    path = Path(email_mod.OUTBOX_PATH)
    assert path.is_file(), f"outbox file was not created at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _post_email(client, report_id, payload):
    resp = client.post(f"/api/v1/reports/{report_id}/email", json=payload)
    if resp.status_code in (404, 405):
        # 405: only GET /api/v1/reports/{report_id} exists, so POST to the
        # email sub-path is "Method Not Allowed" — the email route itself
        # has not landed.
        pytest.fail(
            "BLOCKER: email route POST /api/v1/reports/{report_id}/email "
            f"is not implemented yet (got HTTP {resp.status_code}; route "
            "owned by another agent). reports/email.py exists and is "
            "unit-tested below, but the API route that calls "
            "send_or_queue has not landed."
        )
    return resp


def _report_id(completed_scan):
    report_id = completed_scan["scan"].get("report_id")
    assert report_id, "completed scan must carry report_id"
    return report_id


# -- API tests (need the route) ---------------------------------------


def test_email_invalid_address_returns_422(client, completed_scan):
    report_id = _report_id(completed_scan)
    resp = _post_email(
        client, report_id, {"email": "not-an-email", "format": "docx"}
    )
    assert resp.status_code == 422, (
        f"invalid email must be 422, got {resp.status_code}: {resp.text[:300]}"
    )


def test_email_valid_address_queues_locally_without_smtp(
    client, completed_scan
):
    report_id = _report_id(completed_scan)
    resp = _post_email(
        client, report_id, {"email": "user@example.com", "format": "docx"}
    )
    assert resp.status_code == 200, (
        f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    )
    body = resp.json()
    assert body["status"] == "queued_locally"
    assert body["email"] == "user@example.com"
    assert body["report_id"] == report_id
    assert body.get("download_urls"), "response must carry download_urls"
    assert body.get("mailto", "").startswith("mailto:user@example.com")
    assert "not" in body.get("message", "").lower() or "no smtp" in body.get(
        "message", ""
    ).lower(), "message must honestly say the mail was not sent"

    records = _read_outbox()
    assert len(records) == 1
    record = records[0]
    assert record["email"] == "user@example.com"
    assert record["report_id"] == report_id
    assert record["status"] == "queued_locally"
    assert record["timestamp"]


def test_email_response_files_exist_on_disk(client, completed_scan):
    """The docx/pdf files referenced for the report exist on disk."""
    report_id = _report_id(completed_scan)
    resp = _post_email(
        client, report_id, {"email": "user@example.com", "format": "both"}
    )
    assert resp.status_code == 200, (
        f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    )
    body = resp.json()
    assert body["status"] == "queued_locally"

    records = _read_outbox()
    assert records, "outbox must contain the queued record"
    files = records[-1].get("files") or {}
    assert files, "outbox record must reference the generated writeup files"
    for fmt, fpath in files.items():
        assert Path(fpath).is_file(), (
            f"generated {fmt} writeup missing on disk: {fpath}"
        )

    # The download URLs in the response must also serve the files.
    for fmt, url in (body.get("download_urls") or {}).items():
        got = client.get(url)
        if got.status_code == 404:
            pytest.fail(
                "BLOCKER: download route "
                f"{url} is not implemented yet (owned by another agent); "
                "the writeup file itself exists on disk, but the download "
                "endpoint has not landed."
            )
        assert got.status_code == 200, (
            f"download {fmt} at {url} failed: {got.status_code}"
        )


# -- Unit tests (send_or_queue directly, no route needed) -------------


def _dummy_files(tmp_path):
    docx = tmp_path / "writeup.docx"
    pdf = tmp_path / "writeup.pdf"
    docx.write_bytes(b"fake-docx-bytes")
    pdf.write_bytes(b"fake-pdf-bytes")
    return {"docx": str(docx), "pdf": str(pdf)}


def test_send_or_queue_no_smtp_queues_locally(tmp_path):
    files = _dummy_files(tmp_path)
    result = send_or_queue(
        "user@example.com", "rep_test123", "both", files
    )
    assert result["status"] == "queued_locally"
    assert result["email"] == "user@example.com"
    assert result["report_id"] == "rep_test123"
    assert result["download_urls"] == {
        "docx": "/api/v1/reports/rep_test123/download?format=docx",
        "pdf": "/api/v1/reports/rep_test123/download?format=pdf",
    }
    assert result["mailto"].startswith("mailto:user@example.com")
    assert "GHOSTPATH" in result["mailto"]
    assert "not" in result["message"].lower()

    records = _read_outbox()
    assert len(records) == 1
    assert records[0]["status"] == "queued_locally"
    assert records[0]["files"] == files
    assert records[0]["format"] == "both"


def test_send_or_queue_rejects_invalid_email(tmp_path):
    files = _dummy_files(tmp_path)
    for bad in ("not-an-email", "a@b", "a@b.c", "", "a b@c.com", "@example.com"):
        with pytest.raises(ValueError):
            send_or_queue(bad, "rep_test123", "docx", files)
    # The outbox must not have been touched by the rejected calls.
    assert not Path(email_mod.OUTBOX_PATH).exists()


def test_send_or_queue_smtp_unreachable_falls_back(tmp_path, monkeypatch):
    files = _dummy_files(tmp_path)
    monkeypatch.setenv("GHOSTPATH_SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("GHOSTPATH_SMTP_PORT", "9")  # discard port: closed
    monkeypatch.setenv("GHOSTPATH_SMTP_USER", "sender@example.com")
    monkeypatch.setenv("GHOSTPATH_SMTP_PASS", "SECRET-PASS-xyz-123")
    result = send_or_queue(
        "user@example.com", "rep_test123", "pdf", files
    )
    assert result["status"] == "queued_locally"
    assert result.get("error"), "fallback record must carry the error"
    assert "SECRET-PASS-xyz-123" not in json.dumps(result)
    assert "SECRET-PASS-xyz-123" not in Path(email_mod.OUTBOX_PATH).read_text(
        encoding="utf-8"
    )
    records = _read_outbox()
    assert records[0]["status"] == "queued_locally"
    assert "error" in records[0]


class _FakeSMTP:
    """Stand-in for smtplib.SMTP; records what the module asked it to do."""

    last = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_started = False
        self.login_args = None
        self.sent = None
        _FakeSMTP.last = self

    def starttls(self):
        self.tls_started = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent = msg

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_send_or_queue_smtp_success(tmp_path, monkeypatch):
    files = _dummy_files(tmp_path)
    monkeypatch.setenv("GHOSTPATH_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("GHOSTPATH_SMTP_PORT", "587")
    monkeypatch.setenv("GHOSTPATH_SMTP_USER", "sender@example.com")
    monkeypatch.setenv("GHOSTPATH_SMTP_PASS", "SECRET-PASS-xyz-123")
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    result = send_or_queue(
        "user@example.com", "rep_test123", "both", files
    )
    assert result["status"] == "sent"
    assert result["download_urls"]["docx"].endswith("format=docx")
    assert "SECRET-PASS-xyz-123" not in json.dumps(result)

    fake = _FakeSMTP.last
    assert fake.host == "smtp.example.com"
    assert fake.port == 587
    assert fake.timeout == 10
    assert fake.tls_started, "STARTTLS must be used"
    assert fake.login_args == ("sender@example.com", "SECRET-PASS-xyz-123")
    assert fake.sent["To"] == "user@example.com"
    assert fake.sent["From"] == "sender@example.com"
    assert "rep_test123" in fake.sent["Subject"]
    attachments = list(fake.sent.iter_attachments())
    assert {a.get_filename() for a in attachments} == {
        "writeup.docx",
        "writeup.pdf",
    }


def test_mailto_link_is_url_encoded(tmp_path):
    files = _dummy_files(tmp_path)
    result = send_or_queue(
        "user@example.com", "rep_test123", "docx", files
    )
    mailto = result["mailto"]
    assert mailto.startswith("mailto:user@example.com?subject=")
    # The em dash in the subject must be percent-encoded, not raw.
    assert "\u2014" not in mailto
    assert "%E2%80%94" in mailto
