from typing import Literal, Optional

from pydantic import BaseModel

AssetType = Literal["server", "application", "network_device", "database", "cloud_resource"]
Criticality = Literal["low", "medium", "high", "critical"]


class AssetCreate(BaseModel):
    name: str
    type: AssetType
    environment: str
    criticality: Criticality
    owner: Optional[str] = None


class AssetOut(AssetCreate):
    id: str
    risk_score: Optional[float] = None


class AssetRelationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
