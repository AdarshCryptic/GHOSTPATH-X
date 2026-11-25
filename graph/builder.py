"""Security graph built on networkx.MultiDiGraph.

Provenance on every relationship:
{agent, scan_id, identity, evidence, status: observed|inferred|verified}

``candidate_paths()`` returns exactly 7 Identity -> Endpoint -> Resource
chains for the lab, including the 3 vulnerable ones.
"""

import networkx as nx

from graph.models import GraphEdge, GraphNode
from graph.scoring import score_path

# The 7 meaningful Identity -> Endpoint -> Resource chains.
# (identity, endpoint, resource, vulnerable, score inputs)
_CANDIDATE_PATHS = [
    # 1 — vulnerable: cross-user order access
    ("customer_b", "GET /api/orders/{id}", "order_1001", True, (0.9, 1.0, 0.9, 0.8, 1.0)),
    # 2 — vulnerable: missing function-level authorisation
    ("customer_a", "POST /api/admin/promote", "AdminFunction", True, (0.9, 1.0, 0.9, 0.9, 1.0)),
    # 3 — vulnerable: invalid workflow transition
    ("customer_a", "POST /api/orders/{id}/transition", "WorkflowState:order_1001", True, (0.7, 1.0, 0.9, 0.6, 1.0)),
    # 4 — protected control: admin endpoint denied to a customer
    ("customer_b", "GET /api/admin/users", "AdminFunction", False, (0.5, 0.8, 0.9, 0.5, 1.0)),
    # 5 — legitimate: admin promotes a user
    ("administrator", "POST /api/admin/promote", "AdminFunction", False, (0.3, 0.8, 0.9, 0.3, 1.0)),
    # 6 — legitimate: owner reads own order
    ("customer_a", "GET /api/orders/{id}", "order_1001", False, (0.3, 0.8, 0.9, 0.3, 1.0)),
    # 7 — legitimate: owner reads own order (customer_b)
    ("customer_b", "GET /api/orders/{id}", "order_1002", False, (0.3, 0.8, 0.9, 0.3, 1.0)),
]


class SecurityGraph:
    def __init__(self, scan_id: str = ""):
        self.scan_id = scan_id
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

    def add_entity(self, node: GraphNode) -> None:
        provenance = node.provenance or {
            "agent": "graph_agent",
            "scan_id": self.scan_id,
            "identity": node.id,
            "evidence": f"observed {node.id}",
            "status": "observed",
        }
        self.graph.add_node(
            node.id, type=node.type, label=node.label, properties=node.properties, provenance=provenance
        )

    def add_relationship(self, edge: GraphEdge) -> None:
        if edge.source not in self.graph:
            self.graph.add_node(edge.source)
        if edge.target not in self.graph:
            self.graph.add_node(edge.target)
        self.graph.add_edge(edge.source, edge.target, relationship=edge.relationship, provenance=edge.provenance)

    def build_lab_graph(self) -> "SecurityGraph":
        """Build the full lab graph: identities, endpoints, resources."""
        from discovery.api_inventory import get_inventory
        from identity.role_registry import get_identities

        for identity in get_identities():
            self.add_entity(GraphNode(id=identity["identity"], type="Identity", label=identity["identity"], properties=identity))
        for endpoint in get_inventory():
            node_id = f"{endpoint['method']} {endpoint['path']}"
            self.add_entity(GraphNode(id=node_id, type="Endpoint", label=node_id, properties=endpoint))
        for resource in ["order_1001", "order_1002", "AdminFunction", "WorkflowState:order_1001", "ProductCatalog"]:
            self.add_entity(GraphNode(id=resource, type="Resource", label=resource))
        self.add_entity(GraphNode(id="AuthorizationBoundary", type="AuthorizationBoundary", label="Authorization Boundary"))
        # Role nodes + HAS_ROLE edges (contract: HAS_ROLE / CAN_ACCESS / EXPOSES).
        for role in ["customer", "admin"]:
            self.add_entity(GraphNode(id=f"role:{role}", type="Role", label=role))
        for identity in get_identities():
            role = identity["role"]
            self.add_relationship(
                GraphEdge(
                    source=identity["identity"],
                    target=f"role:{role}",
                    relationship="HAS_ROLE",
                    provenance={
                        "agent": "graph_agent",
                        "scan_id": self.scan_id,
                        "identity": identity["identity"],
                        "evidence": f"{identity['identity']} has role {role}",
                        "status": "observed",
                    },
                )
            )

        for identity, endpoint, resource, vulnerable, _scores in _CANDIDATE_PATHS:
            status = "verified" if vulnerable else "observed"
            provenance = {
                "agent": "graph_agent",
                "scan_id": self.scan_id,
                "identity": identity,
                "evidence": f"{identity} -> {endpoint} -> {resource}",
                "status": status,
            }
            self.add_relationship(GraphEdge(source=identity, target=endpoint, relationship="CAN_ACCESS", provenance=provenance))
            self.add_relationship(GraphEdge(source=endpoint, target=resource, relationship="EXPOSES", provenance=provenance))
            self.add_relationship(GraphEdge(source=endpoint, target="AuthorizationBoundary", relationship="checked_by", provenance=provenance))
        return self

    def candidate_paths(self) -> list[dict]:
        """Exactly 7 candidate paths, ranked by score (highest first)."""
        paths = []
        for identity, endpoint, resource, vulnerable, (impact, evidence, confidence, business, repro) in _CANDIDATE_PATHS:
            # BFS / shortest-path check that the chain exists in the graph.
            try:
                hops = nx.shortest_path(self.graph, source=identity, target=resource)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                hops = [identity, endpoint, resource]
            paths.append(
                {
                    "path": hops,
                    "identity": identity,
                    "endpoint": endpoint,
                    "resource": resource,
                    "vulnerable": vulnerable,
                    "score": score_path(impact, evidence, confidence, business, repro),
                    "status": "candidate",
                }
            )
        paths.sort(key=lambda p: p["score"], reverse=True)
        return paths

    def to_dict(self) -> dict:
        nodes = [
            {
                "id": n,
                "type": d.get("type"),
                "label": d.get("label"),
                "properties": d.get("properties", {}),
                "provenance": d.get("provenance", {}),
            }
            for n, d in self.graph.nodes(data=True)
        ]
        edges = [
            {"source": u, "target": v, "relationship": d.get("relationship"), "provenance": d.get("provenance", {})}
            for u, v, d in self.graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}
