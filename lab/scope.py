"""Scope validation: a lab is in scope only if its base URL passes policy."""

from core.policy import LabPolicy, check_url_allowed


def validate_scope(base_url: str, policy: LabPolicy | None = None) -> dict:
    """Return {"in_scope": bool, "reason": str} for *base_url*."""
    if check_url_allowed(base_url, policy):
        return {"in_scope": True, "reason": "base_url is inside the lab allowlist"}
    return {"in_scope": False, "reason": "base_url is outside the lab allowlist"}


def enforce_scope(base_url: str, policy: LabPolicy | None = None) -> None:
    result = validate_scope(base_url, policy)
    if not result["in_scope"]:
        raise ValueError(result["reason"])
