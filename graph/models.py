"""Graph node / edge models."""

from typing import Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    type: Literal[
        "Identity",
        "Role",
        "Endpoint",
        "Resource",
        "Permission",
        "Workflow",
        "State",
        "Finding",
        "Session",
        "AuthorizationBoundary",
    ]
    label: str
    properties: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    provenance: dict = Field(default_factory=dict)
