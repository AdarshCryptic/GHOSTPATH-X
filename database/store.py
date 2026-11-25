"""In-memory store (stdlib + pydantic only). Singleton ``STORE``."""

import secrets
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(4)}"


class Store:
    def __init__(self) -> None:
        self.labs: dict[str, dict] = {}
        self.scans: dict[str, dict] = {}
        self.findings: dict[str, dict] = {}
        self.reports: dict[str, dict] = {}
        self.challenge_attempts: dict[str, dict] = {}
        self.audit: list[dict] = []
        self._finding_counters: dict[str, int] = {}

    # -- labs ---------------------------------------------------------
    def create_lab(self, lab: dict) -> dict:
        lab_id = _new_id("lab_")
        record = {"id": lab_id, **lab}
        self.labs[lab_id] = record
        return record

    def get_lab(self, lab_id: str) -> dict | None:
        return self.labs.get(lab_id)

    def list_labs(self) -> list[dict]:
        return list(self.labs.values())

    # -- scans --------------------------------------------------------
    def create_scan(self, scan: dict) -> dict:
        scan_id = _new_id("scan_")
        record = {
            "id": scan_id,
            "status": "running",
            "progress": 0,
            "phase": "Discovery",
            "agent_status": [],
            "endpoints_discovered": 0,
            "identities_mapped": 0,
            "attack_paths": 0,
            "validated_findings": 0,
            **scan,
        }
        self.scans[scan_id] = record
        self._finding_counters[scan_id] = 0
        return record

    def get_scan(self, scan_id: str) -> dict | None:
        return self.scans.get(scan_id)

    def update_scan(self, scan_id: str, updates: dict) -> dict | None:
        scan = self.scans.get(scan_id)
        if scan is None:
            return None
        scan.update(updates)
        return scan

    def list_scans(self) -> list[dict]:
        return list(self.scans.values())

    # -- findings -----------------------------------------------------
    def add_finding(self, scan_id: str, finding: dict) -> dict:
        self._finding_counters[scan_id] = self._finding_counters.get(scan_id, 0) + 1
        seq = self._finding_counters[scan_id]
        finding_id = finding.get("id") or f"FIND-{seq:03d}"
        record = {"id": finding_id, "scan_id": scan_id, **finding}
        # Keep the explicit id if supplied (it already equals FIND-xxx).
        record["id"] = finding_id
        self.findings[finding_id] = record
        return record

    def list_findings(self, scan_id: str | None = None) -> list[dict]:
        if scan_id is None:
            return list(self.findings.values())
        return [f for f in self.findings.values() if f.get("scan_id") == scan_id]

    def get_finding(self, finding_id: str) -> dict | None:
        return self.findings.get(finding_id)

    # -- reports ------------------------------------------------------
    def add_report(self, report: dict) -> dict:
        report_id = _new_id("rep_")
        record = {"id": report_id, **report}
        self.reports[report_id] = record
        return record

    def get_report(self, report_id: str) -> dict | None:
        return self.reports.get(report_id)

    def list_reports(self) -> list[dict]:
        return list(self.reports.values())

    # -- challenge attempts --------------------------------------------
    def add_challenge_attempt(self, attempt: dict) -> dict:
        attempt_id = _new_id("att_")
        record = {"id": attempt_id, **attempt}
        self.challenge_attempts[attempt_id] = record
        return record

    def list_challenge_attempts(self, challenge_id: str | None = None) -> list[dict]:
        attempts = list(self.challenge_attempts.values())
        if challenge_id is None:
            return attempts
        return [a for a in attempts if a.get("challenge_id") == challenge_id]

    def get_challenge_attempt(self, attempt_id: str) -> dict | None:
        return self.challenge_attempts.get(attempt_id)


STORE = Store()
