"""Email delivery for GHOSTPATH X attack writeups (v0.2).

Stdlib only (``smtplib`` / ``email``) — no new dependency.

SMTP credentials come ONLY from environment variables; nothing is
hardcoded and the password is never logged. When no SMTP is configured
(the normal case for a lab install), the writeup is NOT pretended to
have been sent: it is generated, queued locally in
``reports/outbox.json``, and the caller gets download + ``mailto:``
links so the user can send it themselves.

Public entry point: :func:`send_or_queue`.
"""

import json
import logging
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

SMTP_TIMEOUT_SECONDS = 10

# Overridable for tests (tests monkeypatch this to a tmp path so no test
# record ever lands in the real outbox).
OUTBOX_PATH = Path(__file__).resolve().parent / "outbox.json"

_MIME_TYPES = {
    "docx": (
        "application",
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    "pdf": ("application", "pdf"),
}


def _subject(report_id: str) -> str:
    return f"GHOSTPATH X \u2014 Attack Writeup {report_id}"


def _body_text(report_id: str, download_urls: dict) -> str:
    lines = [
        "Hello,",
        "",
        f"Your GHOSTPATH X attack writeup for report {report_id} is ready.",
        "",
    ]
    if download_urls:
        lines.append("Download it from the GHOSTPATH X dashboard:")
        for fmt, url in download_urls.items():
            lines.append(f"  - {fmt}: {url}")
        lines.append("")
    lines.append(
        "The writeup file(s) are attached to this email when it was sent "
        "by SMTP; when no SMTP server is configured, use the download "
        "links above (or the mailto link in the dashboard) instead."
    )
    lines.append("")
    lines.append("GHOSTPATH X — Follow the ghost. Prove the path.")
    return "\n".join(lines)


def _download_urls(report_id: str, files: dict) -> dict:
    return {
        fmt: f"/api/v1/reports/{report_id}/download?format={fmt}"
        for fmt in files
    }


def _mailto_link(email: str, report_id: str) -> str:
    body = (
        "Hello,\n\n"
        f"Your GHOSTPATH X attack writeup for report {report_id} is "
        "attached / ready to download from the GHOSTPATH X dashboard.\n\n"
        "GHOSTPATH X — Follow the ghost. Prove the path."
    )
    return (
        f"mailto:{email}"
        f"?subject={quote(_subject(report_id), safe='')}"
        f"&body={quote(body, safe='')}"
    )


def _smtp_config() -> dict:
    """Read SMTP config from env only. Never hardcode credentials."""
    try:
        port = int(os.environ.get("GHOSTPATH_SMTP_PORT", "587") or "587")
    except ValueError:
        port = 587
    user = os.environ.get("GHOSTPATH_SMTP_USER", "")
    return {
        "host": os.environ.get("GHOSTPATH_SMTP_HOST", ""),
        "port": port,
        "user": user,
        "password": os.environ.get("GHOSTPATH_SMTP_PASS", ""),
        # Default sender is the SMTP user.
        "from": os.environ.get("GHOSTPATH_SMTP_FROM", "") or user,
    }


def _queue_record(
    email: str, report_id: str, fmt: str, files: dict, error: str | None = None
) -> dict:
    """Append one queued-locally record to the outbox file.

    The record holds only metadata (addresses, ids, file paths) — never
    file contents and never secrets.
    """
    record = {
        "email": email,
        "report_id": report_id,
        "format": fmt,
        "files": dict(files),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "queued_locally",
    }
    if error is not None:
        record["error"] = error
    path = Path(OUTBOX_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                records = data
        except (json.JSONDecodeError, OSError):
            records = []
    records.append(record)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record


def send_or_queue(email: str, report_id: str, format: str, files: dict) -> dict:
    """Send a writeup by email, or queue it locally when that is not possible.

    ``files`` maps ``"docx"`` / ``"pdf"`` to absolute paths that exist.

    Returns ``{"status": "sent", ...}`` on a successful SMTP send, or
    ``{"status": "queued_locally", ...}`` when no SMTP is configured or
    sending failed. The queued case never pretends the mail went out:
    the message says so honestly, and the response carries
    ``download_urls`` + a ``mailto`` link.

    Raises ``ValueError`` for an invalid email address (the API route
    maps that to HTTP 422). Never raises for an SMTP failure — that
    falls back to queueing locally.
    """
    if not isinstance(email, str) or not EMAIL_RE.match(email):
        raise ValueError(f"invalid email address: {email!r}")

    files = dict(files or {})
    download_urls = _download_urls(report_id, files)
    mailto = _mailto_link(email, report_id)
    cfg = _smtp_config()

    if not cfg["host"] or not cfg["user"] or not cfg["password"]:
        _queue_record(email, report_id, format, files)
        # Log host + whether auth is configured only — never the password.
        logger.info(
            "SMTP not configured (host=%s, auth configured=%s); "
            "writeup %s queued locally for %s",
            cfg["host"] or "(unset)",
            bool(cfg["user"] and cfg["password"]),
            report_id,
            email,
        )
        return {
            "status": "queued_locally",
            "email": email,
            "report_id": report_id,
            "format": format,
            "download_urls": download_urls,
            "mailto": mailto,
            "message": (
                "No SMTP server is configured, so the writeup was not "
                "emailed. It has been generated and queued locally — "
                "download it from the links above or use the mailto link "
                "to send it yourself."
            ),
        }

    try:
        msg = EmailMessage()
        msg["From"] = cfg["from"] or cfg["user"]
        msg["To"] = email
        msg["Subject"] = _subject(report_id)
        msg.set_content(_body_text(report_id, download_urls))
        for fmt, fpath in files.items():
            path = Path(fpath)
            if not path.is_file():
                continue
            maintype, subtype = _MIME_TYPES.get(
                fmt, ("application", "octet-stream")
            )
            msg.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )
        with smtplib.SMTP(
            cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT_SECONDS
        ) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 - SMTP must never crash the request
        error = f"{type(exc).__name__}: {exc}"
        if cfg["password"]:
            error = error.replace(cfg["password"], "[redacted]")
        _queue_record(email, report_id, format, files, error=error)
        logger.warning(
            "SMTP send failed (%s); writeup %s queued locally for %s",
            type(exc).__name__,
            report_id,
            email,
        )
        return {
            "status": "queued_locally",
            "email": email,
            "report_id": report_id,
            "format": format,
            "download_urls": download_urls,
            "mailto": mailto,
            "error": error,
            "message": (
                f"Email could not be sent ({type(exc).__name__}), so the "
                "writeup was not emailed. It has been generated and queued "
                "locally — download it from the links above or use the "
                "mailto link to send it yourself."
            ),
        }

    logger.info(
        "Writeup %s emailed to %s via SMTP host %s",
        report_id,
        email,
        cfg["host"],
    )
    return {
        "status": "sent",
        "email": email,
        "report_id": report_id,
        "format": format,
        "download_urls": download_urls,
        "mailto": mailto,
        "message": f"Writeup emailed to {email}.",
    }
