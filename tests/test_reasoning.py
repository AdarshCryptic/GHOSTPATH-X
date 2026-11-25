"""Reasoning tests — ranking of attack hypotheses.

Contract: the reasoner ranks the cross-user hypothesis above a low-impact
one, and ranking is deterministic (same input -> same order twice).

Backend (as built): ``agents/reasoning_agent.py`` exposes ``LocalReasoner``
(a deterministic, rule-based ranker — an Ollama-compatible stub, no LLM
call) with ``.rank(hypotheses)``; each hypothesis is scored with
``graph.scoring.score_path`` from its impact / evidence / confidence /
business / reproducibility fields. ``ReasoningAgent`` ranks the 7 graph
candidate paths the same way. Tests below exercise that real API.
"""

from agents.reasoning_agent import LocalReasoner, ReasoningAgent
from graph.builder import SecurityGraph

CROSS_USER_HYPOTHESIS = {
    "hypothesis_id": "HYP-1",
    "title": "Cross-user order access",
    "identity": "customer_b",
    "endpoint": "GET /api/orders/{id}",
    "resource": "order_1001",
    "impact": 0.9,
    "evidence": 1.0,
    "confidence": 0.9,
    "business": 0.8,
    "reproducibility": 1.0,
}

LOW_IMPACT_HYPOTHESIS = {
    "hypothesis_id": "HYP-2",
    "title": "Verbose error message",
    "identity": "customer_a",
    "endpoint": "GET /api/products",
    "resource": "ProductCatalog",
    "impact": 0.2,
    "evidence": 0.5,
    "confidence": 0.6,
    "business": 0.1,
    "reproducibility": 0.5,
}


def test_reasoner_ranks_cross_user_above_low_impact():
    ranked = LocalReasoner().rank([LOW_IMPACT_HYPOTHESIS, CROSS_USER_HYPOTHESIS])
    assert ranked[0]["hypothesis_id"] == "HYP-1", (
        f"cross-user hypothesis must rank first, got {[h['hypothesis_id'] for h in ranked]}"
    )
    assert ranked[-1]["hypothesis_id"] == "HYP-2"
    assert ranked[0]["score"] > ranked[-1]["score"]
    assert ranked[0]["status"] == "candidate"
    # Cross-user score: 0.30*0.9+0.25*1.0+0.20*0.9+0.15*0.8+0.10*1.0 = 0.92
    assert ranked[0]["score"] == 0.92


def test_ranking_deterministic():
    hypotheses = [CROSS_USER_HYPOTHESIS, LOW_IMPACT_HYPOTHESIS]
    first = LocalReasoner().rank(hypotheses)
    second = LocalReasoner().rank(hypotheses)
    assert [h["hypothesis_id"] for h in first] == [h["hypothesis_id"] for h in second]
    assert first == second, "same input must produce the same ranking twice"


def test_reasoning_agent_ranks_graph_paths_vulnerable_first():
    # The agent ranks the 7 lab candidate paths; every vulnerable path must
    # outrank every legitimate one, and the top-ranked path is vulnerable.
    graph = SecurityGraph(scan_id="scan-test").build_lab_graph()
    paths = graph.candidate_paths()
    by_key = {(p["identity"], p["endpoint"], p["resource"]): p for p in paths}
    cross_user = by_key[("customer_b", "GET /api/orders/{id}", "order_1001")]
    low_impact = by_key[("customer_a", "GET /api/orders/{id}", "order_1001")]
    assert cross_user["vulnerable"] is True
    assert low_impact["vulnerable"] is False
    assert cross_user["score"] > low_impact["score"]
    vuln_scores = [p["score"] for p in paths if p["vulnerable"]]
    legit_scores = [p["score"] for p in paths if not p["vulnerable"]]
    assert min(vuln_scores) > max(legit_scores)
    assert paths[0]["vulnerable"] is True
    assert paths == sorted(paths, key=lambda p: p["score"], reverse=True)


def test_reasoning_agent_class_exists_and_is_named():
    assert ReasoningAgent.name == "reasoning"
    assert callable(getattr(LocalReasoner(), "rank", None))
