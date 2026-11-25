"""Fake session manager for lab-only test accounts.

Sessions are simulated in-process. The string "lab-only-not-real" is a
label marking a value as a lab-only placeholder — it is never a real
credential and is never used to authenticate anything.
"""

LAB_PASSWORD_LABEL = "lab-only-not-real"

_sessions: dict[str, dict] = {}


class SessionManager:
    def create_session(self, identity: str) -> dict:
        session = {
            "identity": identity,
            "session_id": f"session-{identity}",
            "valid": True,
            "credential_label": LAB_PASSWORD_LABEL,
        }
        _sessions[identity] = session
        return dict(session)

    def invalidate(self, identity: str) -> None:
        session = _sessions.get(identity)
        if session is not None:
            session["valid"] = False

    def is_valid(self, identity: str) -> bool:
        return bool(_sessions.get(identity, {}).get("valid", False))

    def get_session(self, identity: str) -> dict | None:
        session = _sessions.get(identity)
        return dict(session) if session else None
