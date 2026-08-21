from typing import Any

from pydantic import BaseModel, Field


class TopologyNode(BaseModel):
    id: str
    entity_id: str | None = None
    label: str
    type: str
    asset_type: str | None = None
    risk_level: str | None = None
    criticality: str | None = None
    ip_address: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    category: str = "other"
    source_interface: str | None = None
    target_interface: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyGraph(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)
    truncated: bool = False
