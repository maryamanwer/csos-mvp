from typing import Any

from pydantic import BaseModel, Field


class TopologyNode(BaseModel):
    id: str
    entity_id: str | None = None
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyGraph(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)
