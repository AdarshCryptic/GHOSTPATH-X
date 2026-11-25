"""Lab policy engine.

Only literal allowed hosts are permitted — no DNS lookup to an external
resolver (DNS-rebinding defence). Private, metadata, and public IPs are
blocked. Every validation test must call a policy check first.
"""

import ipaddress
import time
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from core.security import redact_secrets

BLOCKED_IPS = {
    "169.254.169.254",  # cloud metadata endpoint
}


class LabPolicy(BaseModel):
    allowed_hosts: list[str] = Field(default=["127.0.0.1", "lab.local"])
    allowed_networks: list[str] = Field(default=["127.0.0.0/8"])
    max_requests_per_minute: int = 60
    max_concurrent_tasks: int = 3
    max_scan_duration_minutes: int = 60
    allow_external_network: bool = False
    allow_state_changing_tests: bool = False


DEFAULT_POLICY = LabPolicy()


def is_host_allowed(host: str, policy: LabPolicy | None = None) -> bool:
    """True only for a literal allowed host / allowed network.

    No DNS resolution is performed: a hostname is allowed only if it is
    literally listed in ``allowed_hosts``. IP literals are allowed only
    inside ``allowed_networks``.
    """
    policy = policy or DEFAULT_POLICY
    host = (host or "").strip().lower()
    if not host:
        return False
    if host in BLOCKED_IPS:
        return False
    if host in [h.lower() for h in policy.allowed_hosts]:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Non-literal hostname, not in the allowlist: deny (no DNS lookup).
        return False
    if str(ip) in BLOCKED_IPS:
        return False
    # Private / loopback-external / public addresses are denied unless the
    # address falls inside an explicitly allowed network.
    for network in policy.allowed_networks:
        try:
            if ip in ipaddress.ip_network(network):
                return True
        except ValueError:
            continue
    return False


def check_url_allowed(url: str, policy: LabPolicy | None = None) -> bool:
    """Return False for any URL outside the lab (host, metadata IP, redirect target).

    Only http/https URLs to an allowed host are permitted. Callers that
    need an exception should use :func:`enforce_url_allowed`.
    """
    policy = policy or DEFAULT_POLICY
    if policy.allow_external_network:
        return False  # v0.1 never permits external network, even if flagged
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    return is_host_allowed(host, policy)


def enforce_url_allowed(url: str, policy: LabPolicy | None = None) -> None:
    """Raise ValueError if *url* is outside the lab policy."""
    if not check_url_allowed(url, policy):
        raise ValueError(f"URL not allowed by lab policy: {url}")


class RateLimiter:
    """Simple per-minute request counter."""

    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
        self._window_start = time.monotonic()
        self._count = 0

    def allow(self) -> bool:
        now = time.monotonic()
        if now - self._window_start >= 60:
            self._window_start = now
            self._count = 0
        if self._count >= self.max_requests_per_minute:
            return False
        self._count += 1
        return True

    def enforce(self) -> None:
        if not self.allow():
            raise ValueError("Rate limit exceeded: max_requests_per_minute")


# Module-level limiter used by the validation executor.
rate_limiter = RateLimiter(DEFAULT_POLICY.max_requests_per_minute)


def audit_event(event: dict) -> dict:
    """Redact and append an audit event to the in-memory audit log.

    Returns the redacted event. The audit list lives in the store
    (``STORE.audit``) so every event is recorded in one place.
    """
    from database.store import STORE

    redacted = redact_secrets(dict(event))
    STORE.audit.append(redacted)
    return redacted
