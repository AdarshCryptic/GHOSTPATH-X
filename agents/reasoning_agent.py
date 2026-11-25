"""Reasoning agent: rule-based hypothesis ranking.

``LocalReasoner`` is an Ollama-compatible stub: it ranks hypotheses
with the deterministic path scorer only. No network call, no API key,
no LLM invocation — the LLM role in v0.1 is reasoning/proposing, and
that reasoning is implemented as explicit rules here.
"""

from agents.base import AgentInput, AgentOutput, BaseAgent
from database.store import STORE
from graph.builder import SecurityGraph
from graph.scoring import score_path


class LocalReasoner:
    """Deterministic, local hypothesis ranker (Ollama-compatible stub)."""

    def rank(self, hypotheses: list[dict]) -> list[dict]:
        ranked = []
        for hypothesis in hypotheses:
            score = score_path(
                hypothesis.get("impact", 0.5),
                hypothesis.get("evidence", 0.5),
                hypothesis.get("confidence", 0.5),
                hypothesis.get("business", 0.5),
                hypothesis.get("reproducibility", 0.5),
            )
            ranked.append({**hypothesis, "score": score, "status": "candidate"})
        ranked.sort(key=lambda h: h["score"], reverse=True)
        return ranked


class ReasoningAgent(BaseAgent):
    name = "reasoning"

    async def run(self, task: AgentInput) -> AgentOutput:
        graph = SecurityGraph(scan_id=task.scan_id).build_lab_graph()
        hypotheses = [
            {
                "hypothesis_id": f"HYP-{i + 1}",
                "identity": p["identity"],
                "endpoint": p["endpoint"],
                "resource": p["resource"],
                "impact": 0.9 if p["vulnerable"] else 0.3,
                "evidence": 0.8,
                "confidence": 0.9,
                "business": 0.8 if p["vulnerable"] else 0.3,
                "reproducibility": 1.0,
            }
            for i, p in enumerate(graph.candidate_paths())
        ]
        ranked = LocalReasoner().rank(hypotheses)
        return AgentOutput(
            status="complete",
            observations=[{"type": "hypothesis", **h} for h in ranked],
            confidence=0.9,
        )
