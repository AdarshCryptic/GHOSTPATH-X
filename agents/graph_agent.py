"""Graph agent: builds the security graph via graph/builder.py."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from database.store import STORE
from graph.builder import SecurityGraph


class GraphAgent(BaseAgent):
    name = "graph"

    async def run(self, task: AgentInput) -> AgentOutput:
        graph = SecurityGraph(scan_id=task.scan_id).build_lab_graph()
        paths = graph.candidate_paths()
        STORE.update_scan(task.scan_id, {"attack_paths": len(paths)})
        return AgentOutput(
            status="complete",
            observations=[
                {"type": "graph", **graph.to_dict()},
                {"type": "candidate_paths", "paths": paths},
            ],
            confidence=1.0,
        )
