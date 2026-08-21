"""Interactive topology data sourced from the Neo4j Knowledge Graph."""
from fastapi import APIRouter, Depends, Query

from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.topology import TopologyGraph

router = APIRouter(prefix="/topology", tags=["topology"])


@router.get("", response_model=TopologyGraph)
def get_topology(
    focus_asset_id: str | None = Query(
        default=None,
        description="Return the selected asset and its directly connected entities.",
    ),
    relationship_limit: int = Query(default=500, ge=1, le=2000),
    node_limit: int = Query(default=1000, ge=1, le=4000),
    user: dict = Depends(
        require_role("Admin", "Analyst", "Engineer", "Executive", "ComplianceOfficer")
    ),
):
    return neo4j_client.get_topology(
        relationship_limit=relationship_limit,
        node_limit=node_limit,
        focus_asset_id=focus_asset_id,
    )
