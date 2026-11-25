"""Workflow agent: returns the workflow graph states/transitions."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from database.store import STORE
from workflows.state_model import get_invalid_transitions, get_states, get_valid_transitions
from workflows.transition_analyzer import analyze_all


class WorkflowAgent(BaseAgent):
    name = "workflow"

    async def run(self, task: AgentInput) -> AgentOutput:
        return AgentOutput(
            status="complete",
            observations=[
                {"type": "workflow", "states": get_states()},
                {"type": "workflow", "valid_transitions": [list(t) for t in get_valid_transitions()]},
                {"type": "workflow", "invalid_transitions": [list(t) for t in get_invalid_transitions()]},
                {"type": "workflow", "analysis": analyze_all()},
            ],
            confidence=1.0,
        )
