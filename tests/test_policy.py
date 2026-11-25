"""Policy tests — core/policy.py (LabPolicy, is_host_allowed, check_url_allowed).

Contract:
  - allowed_hosts == ["127.0.0.1", "lab.local"], max_requests_per_minute == 60,
    allow_external_network is False
  - must reject: outside host, redirect to an outside host, metadata IP
    169.254.169.254, private IPs (e.g. 10.0.0.5)
  - must accept: http://127.0.0.1:8000/api/products, http://lab.local/api/products
"""

import pytest

from core.policy import (
    LabPolicy,
    RateLimiter,
    check_url_allowed,
    enforce_url_allowed,
    is_host_allowed,
)


def test_outside_host_blocked():
    assert is_host_allowed("evil.example.com") is False
    assert is_host_allowed("attacker.io") is False
    assert check_url_allowed("http://evil.example.com/") is False
    assert check_url_allowed("https://evil.example.com/login") is False


def test_redirect_blocked():
    # The policy has no redirect-following (no network in tests): a redirect
    # is policed by checking the redirect *target* URL itself. Any target
    # outside the lab must be rejected, and enforce_* must raise.
    assert check_url_allowed("http://evil.example.com/callback") is False
    assert check_url_allowed("http://169.254.169.254/latest/meta-data/") is False
    with pytest.raises(ValueError):
        enforce_url_allowed("http://evil.example.com/callback")
    # A lab URL that merely mentions an outside host in its path is still a
    # lab URL (policy checks the host, not the path) — documents the boundary.
    assert check_url_allowed("http://127.0.0.1:8000/redirect?next=http://evil.example.com/") is True


def test_metadata_ip_blocked():
    assert is_host_allowed("169.254.169.254") is False
    assert check_url_allowed("http://169.254.169.254/") is False
    assert check_url_allowed("http://169.254.169.254/latest/meta-data/iam/") is False
    assert check_url_allowed("http://169.254.169.254:80/") is False


def test_private_ip_blocked():
    for host in ("10.0.0.5", "192.168.1.1", "172.16.0.5", "10.255.255.255"):
        assert is_host_allowed(host) is False, f"{host} must be blocked"
        assert check_url_allowed(f"http://{host}/") is False, f"http://{host}/ must be blocked"


def test_allowed_lab_host_passes():
    assert is_host_allowed("127.0.0.1") is True
    assert is_host_allowed("lab.local") is True
    assert check_url_allowed("http://127.0.0.1:8000/api/products") is True
    assert check_url_allowed("http://lab.local/api/products") is True
    assert check_url_allowed("https://lab.local/api/products") is True


def test_rate_limit_fields_present():
    policy = LabPolicy()
    assert policy.allowed_hosts == ["127.0.0.1", "lab.local"]
    assert policy.max_requests_per_minute == 60
    assert policy.allow_external_network is False


def test_rate_limiter_enforces_sixty_per_minute():
    limiter = RateLimiter(max_requests_per_minute=60)
    assert limiter.max_requests_per_minute == 60
    allowed = sum(1 for _ in range(61) if limiter.allow())
    assert allowed == 60, f"expected exactly 60 allowed requests, got {allowed}"
    assert limiter.allow() is False
    with pytest.raises(ValueError):
        RateLimiter(max_requests_per_minute=0).enforce()
