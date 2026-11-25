"""FastAPI app for GHOSTPATH X v0.2 (lab only, 127.0.0.1).

CORS is off. Static files are served from apps/api/static at / when
that directory exists (owned by another agent); otherwise / returns
plain JSON. No secrets appear in responses; errors are {"detail": ...}.
"""

import asyncio
import hashlib
import hmac
import re
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from agents.base import AgentInput
from agents.discovery_agent import DiscoveryAgent
from agents.graph_agent import GraphAgent
from agents.identity_agent import IdentityAgent
from agents.reasoning_agent import ReasoningAgent
from agents.reporting_agent import ReportingAgent
from agents.validation_agent import ValidationAgent
from agents.workflow_agent import WorkflowAgent
from challenges.challenges import (
    challenge_brief,
    get_challenge,
    list_challenges,
    solve_challenge,
)
from core.config import settings
from core.policy import LabPolicy
from ctf_machines.machines import get_machine, list_machines, list_sources, mark_solved
from database.store import STORE
from graph.builder import SecurityGraph
from lab import target as lab_target
from reports import writeup as writeup_mod

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title=settings.app_name, version=settings.version)


# -- schemas ----------------------------------------------------------
class LabCreate(BaseModel):
    name: str
    base_url: str
    environment: str = "lab"
    policy: LabPolicy | None = None


class ScanCreate(BaseModel):
    lab_id: str
    profile: str = "web_application_mvp"
    identities: list[str] = Field(default=["customer_a", "customer_b", "administrator"])
    modules: list[str] = Field(default_factory=list)


class SolveRequest(BaseModel):
    identity: str
    method: str
    path: str
    body: dict | None = None
    session_valid: bool = True


class WriteupRequest(BaseModel):
    format: str = "both"


class EmailRequest(BaseModel):
    email: str
    format: str = "both"


class CTFMachine(BaseModel):
    id: str
    name: str
    source: str
    type: str
    cost_label: str
    difficulty: str
    topics: list[str]
    os: str
    format: str
    homepage_url: str
    description: str
    setup_steps: list[str]
    learnings: list[str]
    solved: bool = False


class CTFSource(BaseModel):
    name: str
    cost_label: str
    type: str
    homepage_url: str
    description: str


class SolvedRequest(BaseModel):
    solved: bool = True


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


# -- owner lock -------------------------------------------------------
# Showcase PIN lock, NOT real authentication: the PIN is stored only as
# a SHA-256 hash (core/config.py), verified server-side with a
# constant-time comparison. A successful unlock issues a random,
# short-lived session token (30 minutes). After 5 failed attempts a
# client is locked out for 60 seconds. Nothing here ever logs a PIN,
# a hash, or a comparison result.
class OwnerUnlockRequest(BaseModel):
    pin: str

    @field_validator("pin", mode="before")
    @classmethod
    def pin_must_be_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("pin must be a string of exactly 6 digits")
        return value


_OWNER_TOKEN_TTL_SECONDS = 1800  # 30 minutes
_OWNER_MAX_FAILURES = 5
_OWNER_LOCKOUT_SECONDS = 60
_OWNER_PIN_RE = re.compile(r"^\d{6}$")

# token -> expiry (epoch seconds). In-memory only, never persisted.
_owner_sessions: dict[str, float] = {}
# client ip -> {"failures": int, "locked_until": float}
_owner_failures: dict[str, dict] = {}

_OWNER_DETAILS = {
    "name": "Adarsh",
    "role": "Official owner and creator of GHOSTPATH X",
    "title": "Security researcher",
    "projects": ["GHOST (AI Agent Hijack Simulator)", "GHOSTPATH X"],
}


def _owner_client_ip(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"


def _prune_owner_sessions(now: float) -> None:
    for token in [t for t, exp in _owner_sessions.items() if exp <= now]:
        del _owner_sessions[token]


def _owner_failure_state(ip: str) -> dict:
    return _owner_failures.setdefault(ip, {"failures": 0, "locked_until": 0.0})


@app.post("/api/v1/owner/unlock")
def owner_unlock(payload: OwnerUnlockRequest, request: Request) -> dict:
    # Format is validated first: a malformed body is not a PIN attempt
    # and does not count towards the failure budget.
    if not isinstance(payload.pin, str) or not _OWNER_PIN_RE.match(payload.pin):
        raise HTTPException(status_code=422, detail="pin must be a string of exactly 6 digits")
    now = time.time()
    ip = _owner_client_ip(request)
    state = _owner_failure_state(ip)
    if state["locked_until"] and now < state["locked_until"]:
        # Generic message: the lockout must not reveal whether the
        # PIN was right.
        raise HTTPException(status_code=429, detail="too many tries, try again later")
    if state["locked_until"] and now >= state["locked_until"]:
        state["failures"] = 0
        state["locked_until"] = 0.0
    supplied_hash = hashlib.sha256(payload.pin.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, settings.owner_pin_hash):
        state["failures"] += 1
        if state["failures"] >= _OWNER_MAX_FAILURES:
            state["locked_until"] = now + _OWNER_LOCKOUT_SECONDS
        raise HTTPException(status_code=401, detail="incorrect PIN")
    # Success: reset this client's failure count and issue a token.
    state["failures"] = 0
    state["locked_until"] = 0.0
    _prune_owner_sessions(now)
    token = secrets.token_urlsafe(32)
    _owner_sessions[token] = now + _OWNER_TOKEN_TTL_SECONDS
    return {"token": token, "expires_in_seconds": _OWNER_TOKEN_TTL_SECONDS}


@app.get("/api/v1/owner/details")
def owner_details(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    now = time.time()
    _prune_owner_sessions(now)
    if not token or token not in _owner_sessions:
        raise HTTPException(status_code=401, detail="unauthorized")
    return dict(_OWNER_DETAILS)
_DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MEDIA = "application/pdf"


def _challenge_public(challenge: dict) -> dict:
    return {
        **challenge,
        "download_url": f"/api/v1/challenges/{challenge['id']}/brief",
    }


def _writeup_result_or_422(fn, *args, **kwargs) -> dict:
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# -- pipeline ---------------------------------------------------------
def run_pipeline(scan_id: str, lab_id: str) -> dict:
    """Run Discovery -> Identity -> Workflow -> Graph -> Reasoning ->
    Validation -> Reporting synchronously."""
    task = AgentInput(lab_id=lab_id, scan_id=scan_id)
    lab = STORE.get_lab(lab_id) or {}

    def set_status(agent_status: list[str], progress: int, phase: str) -> None:
        STORE.update_scan(scan_id, {"agent_status": list(agent_status), "progress": progress, "phase": phase})

    status: list[str] = []
    set_status(status, 5, "Discovery")
    asyncio.run(DiscoveryAgent().run(task))
    status.append("Discovery Complete")
    set_status(status, 20, "Identity")
    asyncio.run(IdentityAgent().run(task))
    status.append("Identity Complete")
    set_status(status, 35, "Workflow")
    asyncio.run(WorkflowAgent().run(task))
    status.append("Workflow Complete")
    set_status(status, 50, "Graph Intelligence")
    asyncio.run(GraphAgent().run(task))
    status.append("Graph Intelligence Complete")
    set_status(status, 60, "Attack Reasoner Active")
    status.append("Attack Reasoner Active")
    asyncio.run(ReasoningAgent().run(task))
    status[-1] = "Attack Reasoner Complete"
    set_status(status, 75, "Validation Running")
    status.append("Validation Running")
    asyncio.run(ValidationAgent().run(task))
    status[-1] = "Validation Complete"
    set_status(status, 90, "Evidence Waiting")
    status.append("Evidence Waiting")
    # validated_findings is final before reporting, so the generated
    # report agrees with the completed scan record. (Endpoints /
    # identities / attack-path counts were already set by their agents.)
    STORE.update_scan(
        scan_id,
        {"validated_findings": len(STORE.list_findings(scan_id))},
    )
    report = asyncio.run(ReportingAgent().run(task))
    report_id = report.observations[0].get("report_id") if report.observations else None
    status[-1] = "Evidence Complete"
    findings = STORE.list_findings(scan_id)
    STORE.update_scan(
        scan_id,
        {
            "agent_status": status,
            "progress": 100,
            "phase": "Validation complete",
            "status": "completed",
            "validated_findings": len(findings),
            "report_id": report_id,
        },
    )
    return STORE.get_scan(scan_id)


# -- labs -------------------------------------------------------------
@app.post("/api/v1/labs", status_code=201)
def create_lab(payload: LabCreate) -> dict:
    lab = STORE.create_lab(
        {
            "name": payload.name,
            "base_url": payload.base_url,
            "environment": payload.environment,
            "policy": (payload.policy or LabPolicy()).model_dump(),
        }
    )
    return lab


@app.get("/api/v1/labs")
def list_labs() -> list[dict]:
    return STORE.list_labs()


@app.get("/api/v1/labs/{lab_id}")
def get_lab(lab_id: str) -> dict:
    lab = STORE.get_lab(lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="lab not found")
    return lab


# -- scans ------------------------------------------------------------
@app.post("/api/v1/scans", status_code=201)
def create_scan(payload: ScanCreate) -> dict:
    lab = STORE.get_lab(payload.lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="lab not found")
    scan = STORE.create_scan(
        {
            "lab_id": payload.lab_id,
            "lab_name": lab.get("name", settings.lab_name),
            "profile": payload.profile,
            "identities": payload.identities,
            "modules": payload.modules,
        }
    )
    return run_pipeline(scan["id"], payload.lab_id)


@app.get("/api/v1/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
    scan = STORE.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return scan


@app.post("/api/v1/scans/{scan_id}/stop")
def stop_scan(scan_id: str) -> dict:
    scan = STORE.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    STORE.update_scan(scan_id, {"status": "stopped"})
    return STORE.get_scan(scan_id)


@app.get("/api/v1/scans/{scan_id}/graph")
def get_scan_graph(scan_id: str) -> dict:
    if STORE.get_scan(scan_id) is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return SecurityGraph(scan_id=scan_id).build_lab_graph().to_dict()


@app.get("/api/v1/scans/{scan_id}/paths")
def get_scan_paths(scan_id: str) -> list[dict]:
    if STORE.get_scan(scan_id) is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return SecurityGraph(scan_id=scan_id).build_lab_graph().candidate_paths()


# -- findings ---------------------------------------------------------
@app.get("/api/v1/findings")
def list_findings(scan_id: str | None = None) -> list[dict]:
    return STORE.list_findings(scan_id)


@app.get("/api/v1/findings/{finding_id}")
def get_finding(finding_id: str) -> dict:
    finding = STORE.get_finding(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="finding not found")
    return finding


# -- reports ----------------------------------------------------------
@app.get("/api/v1/reports/{report_id}")
def get_report(report_id: str) -> dict:
    report = STORE.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report


# -- challenges -------------------------------------------------------
@app.get("/api/v1/challenges")
def list_challenges_route() -> list[dict]:
    return [_challenge_public(c) for c in list_challenges()]


@app.get("/api/v1/challenges/{challenge_id}")
def get_challenge_route(challenge_id: str) -> dict:
    challenge = get_challenge(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="challenge not found")
    return _challenge_public(challenge)


@app.get("/api/v1/challenges/{challenge_id}/brief")
def get_challenge_brief(challenge_id: str) -> PlainTextResponse:
    brief = challenge_brief(challenge_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="challenge not found")
    filename = f"{challenge_id.lower()}-brief.md"
    return PlainTextResponse(
        brief,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/v1/challenges/{challenge_id}/solve")
def solve_challenge_route(challenge_id: str, payload: SolveRequest) -> dict:
    if get_challenge(challenge_id) is None:
        raise HTTPException(status_code=404, detail="challenge not found")
    if payload.identity not in lab_target.IDENTITIES:
        raise HTTPException(status_code=422, detail=f"unknown identity: {payload.identity}")
    if payload.method.upper() not in _VALID_METHODS or not payload.path.startswith("/"):
        raise HTTPException(status_code=422, detail="invalid action: method and path are required")
    result = solve_challenge(
        challenge_id,
        payload.identity,
        payload.method,
        payload.path,
        payload.body,
        payload.session_valid,
    )
    STORE.add_challenge_attempt(
        {
            "challenge_id": challenge_id,
            "identity": payload.identity,
            "method": payload.method.upper(),
            "path": payload.path,
            "body": payload.body or {},
            "session_valid": payload.session_valid,
            "solved": result["solved"],
            "status": result["status"],
            "evidence": result["evidence"],
            "message": result["message"],
        }
    )
    return result


@app.post("/api/v1/challenges/{challenge_id}/writeup")
def challenge_writeup_route(challenge_id: str, payload: WriteupRequest) -> dict:
    if get_challenge(challenge_id) is None:
        raise HTTPException(status_code=404, detail="challenge not found")
    attempts = STORE.list_challenge_attempts(challenge_id)
    result = _writeup_result_or_422(
        writeup_mod.generate_challenge_writeup,
        challenge_id,
        payload.format,
        attempts[-1] if attempts else None,
    )
    return {"challenge_id": challenge_id, **result}


# -- ctf machines -----------------------------------------------------
# /sources is declared before /{machine_id} so "sources" is never
# treated as a machine id.
@app.get("/api/v1/ctf-machines", response_model=list[CTFMachine])
def list_ctf_machines_route(
    source: str | None = None,
    difficulty: str | None = None,
    type: str | None = Query(default=None, alias="type"),
    q: str | None = None,
) -> list[dict]:
    return list_machines(source=source, difficulty=difficulty, machine_type=type, q=q)


@app.get("/api/v1/ctf-machines/sources", response_model=list[CTFSource])
def list_ctf_sources_route() -> list[dict]:
    return list_sources()


@app.get("/api/v1/ctf-machines/{machine_id}", response_model=CTFMachine)
def get_ctf_machine_route(machine_id: str) -> dict:
    machine = get_machine(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="ctf machine not found")
    return machine


@app.post("/api/v1/ctf-machines/{machine_id}/solved", response_model=CTFMachine)
def mark_ctf_machine_solved_route(machine_id: str, payload: SolvedRequest) -> dict:
    machine = mark_solved(machine_id, payload.solved)
    if machine is None:
        raise HTTPException(status_code=404, detail="ctf machine not found")
    return machine


# -- scan writeups ----------------------------------------------------
@app.post("/api/v1/scans/{scan_id}/writeup")
def scan_writeup_route(scan_id: str, payload: WriteupRequest) -> dict:
    if STORE.get_scan(scan_id) is None:
        raise HTTPException(status_code=404, detail="scan not found")
    result = _writeup_result_or_422(writeup_mod.generate_scan_writeup, scan_id, payload.format)
    return {"scan_id": scan_id, **result}


# -- report download / email ------------------------------------------
@app.get("/api/v1/reports/{report_id}/download")
def download_report(report_id: str, format: str = Query("docx")) -> FileResponse:
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=422, detail="format must be docx or pdf")
    report = STORE.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    writeups = report.get("writeups") or {}
    path = writeups.get(format)
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail=f"no {format} writeup for this report")
    media_type = _DOCX_MEDIA if format == "docx" else _PDF_MEDIA
    return FileResponse(path, media_type=media_type, filename=Path(path).name)


@app.post("/api/v1/reports/{report_id}/email")
def email_report(report_id: str, payload: EmailRequest) -> dict:
    if not payload.email or not EMAIL_RE.match(payload.email):
        raise HTTPException(status_code=422, detail="invalid email address")
    if payload.format not in ("docx", "pdf", "both"):
        raise HTTPException(status_code=422, detail="format must be docx, pdf or both")
    report = STORE.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    # Generate the requested writeup file(s) first.
    if report.get("scan_id"):
        result = _writeup_result_or_422(
            writeup_mod.generate_scan_writeup, report["scan_id"], payload.format
        )
    elif report.get("challenge_id"):
        result = _writeup_result_or_422(
            writeup_mod.generate_challenge_writeup, report["challenge_id"], payload.format
        )
    else:
        raise HTTPException(
            status_code=404, detail="report has no scan or challenge to generate a writeup for"
        )
    files = {
        fmt: str(writeup_mod.REPORTS_DIR / filename)
        for fmt, filename in result["files"].items()
    }
    # The sending module is owned by another agent; import it lazily so
    # this route still works (queued locally) before it lands.
    try:
        from reports.email import send_or_queue

        return send_or_queue(payload.email, report_id, payload.format, files)
    except (ImportError, AttributeError):
        return {
            "status": "queued_locally",
            "email": payload.email,
            "report_id": report_id,
            "format": payload.format,
            "files": result["files"],
            "download_urls": result["download_urls"],
            "mailto": (
                f"mailto:{payload.email}"
                f"?subject=GHOSTPATH X writeup {report_id}"
            ),
        }


# -- root / static dashboard (last, so it never shadows /api/v1/*) ----
# API routes above are matched first; / serves the dashboard when
# apps/api/static exists, otherwise plain root JSON.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:

    @app.get("/")
    def root() -> dict:
        return {"app": settings.app_name, "version": settings.version, "lab": settings.lab_name}
