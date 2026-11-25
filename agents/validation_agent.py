"""Validation agent: runs invariants via validation/executor.py."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from validation.executor import build_findings, run_all_invariants, status_for


class ValidationAgent(BaseAgent):
    name = "validation"

    async def run(self, task: AgentInput) -> AgentOutput:
        results = run_all_invariants(task.scan_id)
        findings = build_findings(task.scan_id, results)
        observations = [
            {
                "type": "validation",
                "invariant_id": r.invariant_id,
                "outcome": r.outcome,
                "status": status_for(r),
                "expected": r.expected,
                "observed": r.observed,
                "reproducible": r.reproducible,
            }
            for r in results
        ]
        return AgentOutput(
            status="complete",
            observations=observations + [{"type": "findings", "count": len(findings)}],
            confidence=1.0,
        )
