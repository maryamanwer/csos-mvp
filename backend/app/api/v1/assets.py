"""
Asset inventory endpoints, backed by the Neo4j Knowledge Graph.
TODO(M2): implement create/update/delete + CSV/Excel bulk import.
"""
from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.asset import AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
def list_assets(user: dict = Depends(require_role("Admin", "Engineer", "Analyst", "Executive"))):
    # TODO(M2): pagination, filtering by type/criticality/environment
    rows = neo4j_client.run("MATCH (a:Asset) RETURN a LIMIT 100")
    return [
        AssetOut(
            id=r["a"]["id"],
            name=r["a"]["name"],
            type=r["a"]["type"],
            environment=r["a"]["environment"],
            criticality=r["a"]["criticality"],
            owner=r["a"].get("owner"),
        )
        for r in rows
    ]


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, user: dict = Depends(require_role("Admin", "Engineer", "Analyst", "Executive"))):
    a = neo4j_client.get_asset(asset_id)
    return AssetOut(
        id=a["id"], name=a["name"], type=a["type"], environment=a["environment"],
        criticality=a["criticality"], owner=a.get("owner"),
    )
