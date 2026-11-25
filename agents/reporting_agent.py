"""Reporting agent: assembles the report via reports/generator.py."""

from agents.base import AgentInput, AgentOutput, BaseAgent
from reports.generator import generate_report


class ReportingAgent(BaseAgent):
    name = "reporting"

    async def run(self, task: AgentInput) -> AgentOutput:
        report = generate_report(task.scan_id)
        return AgentOutput(
            status="complete",
            observations=[{"type": "report", "report_id": report["id"], "scan_id": task.scan_id}],
            confidence=1.0,
        )
