"""Graph tests — graph/builder.py (SecurityGraph) + graph/scoring.py.

Contract:
  - nodes contain Identity / Role / Endpoint / Resource types
  - edges contain HAS_ROLE / CAN_ACCESS / EXPOSES
  - provenance present on nodes and edges
  - candidate paths >= 1, scores in [0, 1]
  - score_path() = 0.30*I + 0.25*E + 0.20*C + 0.15*B + 0.10*R

NOTE (integration fix, 2026-11-25): the backend now builds the graph
with node types including "Role" and relationships HAS_ROLE / CAN_ACCESS /
EXPOSES, and every node carries a ``provenance`` key — the contract
tests below pass against the fixed backend.
"""

import pytest

from graph.builder import SecurityGraph
from graph.models import GraphEdge, GraphNode
from graph.scoring import score_path


@pytest.fixture
def lab_graph():
    return SecurityGraph(scan_id="scan-test").build_lab_graph()


def _node_types(graph_dict):
    return {n.get("type") for n in graph_dict["nodes"]}


def _edge_rels(graph_dict):
    return {e.get("relationship") for e in graph_dict["edges"]}


def test_node_types_identity_endpoint_resource(lab_graph):
    types = _node_types(lab_graph.to_dict())
    assert {"Identity", "Endpoint", "Resource"} <= types, f"node types found: {types}"


def test_node_types_include_role_contract(lab_graph):
    # CONTRACT MISMATCH (see module docstring): backend has no "Role" node.
    types = _node_types(lab_graph.to_dict())
    assert "Role" in types, (
        f"contract requires a 'Role' node type; backend node types are {sorted(types)} "
        "(GraphNode type Literal is Identity/Endpoint/Resource/AuthorizationBoundary)"
    )


def test_edge_relationships_match_contract(lab_graph):
    # CONTRACT MISMATCH (see module docstring): backend uses lowercase names.
    rels = _edge_rels(lab_graph.to_dict())
    assert {"HAS_ROLE", "CAN_ACCESS", "EXPOSES"} <= rels, (
        f"contract requires relationships HAS_ROLE/CAN_ACCESS/EXPOSES; "
        f"backend relationships are {sorted(rels)}"
    )


def test_edges_carry_provenance(lab_graph):
    d = lab_graph.to_dict()
    assert d["edge_count"] > 0
    for edge in d["edges"]:
        prov = edge.get("provenance")
        assert isinstance(prov, dict) and prov, f"edge missing provenance: {edge}"
        for key in ("agent", "scan_id", "identity", "evidence", "status"):
            assert key in prov, f"edge provenance missing {key!r}: {prov}"
        assert prov["status"] in ("observed", "inferred", "verified")


def test_nodes_carry_provenance_contract(lab_graph):
    # CONTRACT MISMATCH (see module docstring): nodes carry ``properties``,
    # not a ``provenance`` key.
    d = lab_graph.to_dict()
    assert d["node_count"] > 0
    missing = [n for n in d["nodes"] if not n.get("provenance")]
    assert not missing, (
        f"{len(missing)} node(s) carry no 'provenance' key "
        f"(backend nodes carry 'properties' instead): {[n['id'] for n in missing[:5]]}"
    )


def test_add_entity_and_add_relationship_with_provenance():
    graph = SecurityGraph(scan_id="scan-test")
    graph.add_entity(GraphNode(id="customer_a", type="Identity", label="customer_a"))
    graph.add_entity(GraphNode(id="GET /api/orders/{id}", type="Endpoint", label="GET /api/orders/{id}"))
    graph.add_relationship(GraphEdge(
        source="customer_a",
        target="GET /api/orders/{id}",
        relationship="can_access",
        provenance={"agent": "test", "scan_id": "scan-test", "identity": "customer_a",
                    "evidence": "test", "status": "observed"},
    ))
    d = graph.to_dict()
    assert d["node_count"] == 2
    assert d["edge_count"] == 1
    assert d["edges"][0]["provenance"]["agent"] == "test"


def test_to_dict_counts(lab_graph):
    d = lab_graph.to_dict()
    assert d["node_count"] == len(d["nodes"]) > 0
    assert d["edge_count"] == len(d["edges"]) > 0
    # Lab graph: 3 identities + 8 endpoints + 5 resources + 1 boundary
    # + 2 roles = 19 nodes; edges: 7 paths x 3 + 3 HAS_ROLE = 24.
    assert d["node_count"] == 19, f"expected 19 nodes, got {d['node_count']}"
    assert d["edge_count"] == 24, f"expected 7 paths x 3 edges + 3 HAS_ROLE = 24, got {d['edge_count']}"


def test_candidate_paths_at_least_one_and_scores_in_range(lab_graph):
    paths = lab_graph.candidate_paths()
    assert len(paths) == 7, f"contract lab graph has exactly 7 candidate paths, got {len(paths)}"
    assert len(paths) >= 1
    for p in paths:
        assert 0.0 <= p["score"] <= 1.0, f"score out of [0,1]: {p}"
        assert p["path"][0] == p["identity"]
        assert p["resource"] in p["path"]


def test_candidate_paths_ranked_by_score_descending(lab_graph):
    scores = [p["score"] for p in lab_graph.candidate_paths()]
    assert scores == sorted(scores, reverse=True), "candidate paths must be ranked highest score first"


def test_score_path_known_weights():
    assert score_path(1, 1, 1, 1, 1) == 1.0
    assert score_path(0, 0, 0, 0, 0) == 0.0
    # Each unit input contributes exactly its contract weight.
    assert score_path(1, 0, 0, 0, 0) == 0.30
    assert score_path(0, 1, 0, 0, 0) == 0.25
    assert score_path(0, 0, 1, 0, 0) == 0.20
    assert score_path(0, 0, 0, 1, 0) == 0.15
    assert score_path(0, 0, 0, 0, 1) == 0.10
    # Weighted example: 0.30*0.9 + 0.25*1.0 + 0.20*0.9 + 0.15*0.8 + 0.10*1.0 = 0.92
    assert score_path(0.9, 1.0, 0.9, 0.8, 1.0) == 0.92
    assert 0.0 <= score_path(0.5, 0.5, 0.5, 0.5, 0.5) <= 1.0
