"""Identity agent: returns the 3 lab identities + role map."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from database.store import STORE
from identity.role_registry import get_identities, role_map
from identity.session_manager import SessionManager


class IdentityAgent(BaseAgent):
    name = "identity"

    async def run(self, task: AgentInput) -> AgentOutput:
        identities = get_identities()
        sessions = SessionManager()
        for identity in identities:
            sessions.create_session(identity["identity"])
        STORE.update_scan(task.scan_id, {"identities_mapped": len(identities)})
        return AgentOutput(
            status="complete",
            observations=[{"type": "identity", **i} for i in identities] + [{"type": "role_map", "roles": role_map()}],
            confidence=1.0,
        )
