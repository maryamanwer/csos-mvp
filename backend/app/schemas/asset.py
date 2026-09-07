from typing import Literal, Optional

from pydantic import BaseModel, Field

AssetType = Literal["server", "application", "network_device", "database", "cloud_resource"]
Criticality = Literal["low", "medium", "high", "critical"]


class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    type: AssetType
    environment: str = Field(min_length=2, max_length=100)
    criticality: Criticality
    exposure: Literal["internal", "partner", "internet"] = "internal"
    owner: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=2000)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    type: AssetType | None = None
    environment: str | None = Field(default=None, min_length=2, max_length=100)
    criticality: Criticality | None = None
    exposure: Literal["internal", "partner", "internet"] | None = None
    owner: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
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
        "DEPENDS_ON",
        "HOSTS",
        "COMMUNICATES_WITH",
    ]
    properties: dict = Field(default_factory=dict)


class BulkImportError(BaseModel):
    row: int
    message: str


class BulkImportResult(BaseModel):
    imported: int
    failed: int
    errors: list[BulkImportError] = Field(default_factory=list)
