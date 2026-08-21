from typing import Literal, Optional

from pydantic import BaseModel, Field

AssetType = Literal[
    "server",
    "application",
    "network_device",
    "router",
    "switch",
    "firewall",
    "database",
    "endpoint",
    "workstation",
    "cloud_resource",
    "cloud",
    "other",
]
Criticality = Literal["low", "medium", "high", "critical"]
EdrStatus = Literal["active", "missing", "outdated", "not_applicable", "unknown"]
ManagedStatus = Literal["managed", "unmanaged", "unknown"]


class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    type: AssetType
    environment: str = Field(min_length=2, max_length=100)
    criticality: Criticality
    owner: Optional[str] = Field(default=None, max_length=255)
    hostname: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    operating_system: Optional[str] = Field(default=None, max_length=255)
    edr_status: EdrStatus = "unknown"
    edr_product: Optional[str] = Field(default=None, max_length=255)
    edr_agent_version: Optional[str] = Field(default=None, max_length=100)
    edr_agent_outdated: bool = False
    managed_status: ManagedStatus = "unknown"
    data_sources: list[str] = Field(default_factory=list)
    description: Optional[str] = Field(default=None, max_length=2000)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    type: AssetType | None = None
    environment: str | None = Field(default=None, min_length=2, max_length=100)
    criticality: Criticality | None = None
    owner: str | None = Field(default=None, max_length=255)
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    operating_system: str | None = Field(default=None, max_length=255)
    edr_status: EdrStatus | None = None
    edr_product: str | None = Field(default=None, max_length=255)
    edr_agent_version: str | None = Field(default=None, max_length=100)
    edr_agent_outdated: bool | None = None
    managed_status: ManagedStatus | None = None
    data_sources: list[str] | None = None
    description: str | None = Field(default=None, max_length=2000)


class AssetOut(AssetCreate):
    id: str
    risk_score: Optional[float] = None


class AssetRelationship(BaseModel):
    id: str | None = None
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict = Field(default_factory=dict)


class AssetRelationshipCreate(BaseModel):
    target_id: str
    relationship_type: Literal[
        "CONNECTS_TO",
        "CONNECTED_TO",
        "DEPENDS_ON",
        "HOSTS",
        "COMMUNICATES_WITH",
        "PROTECTED_BY",
        "CONNECTED_THROUGH",
    ]
    properties: dict = Field(default_factory=dict)


class BulkImportError(BaseModel):
    row: int
    message: str


class BulkImportResult(BaseModel):
    imported: int
    failed: int
    errors: list[BulkImportError] = Field(default_factory=list)
