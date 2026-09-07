"""
Risk Engine endpoints (core platform scaffold).
TODO(P4): finalize scoring formula (likelihood x impact x asset criticality weighting).
"""
from fastapi import APIRouter, Depends, Query

from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.risk_compliance import RiskOut

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/top", response_model=list[RiskOut])
def top_risks(
    limit: int = Query(5, ge=1, le=1000),
    user: dict = Depends(require_role("Admin", "Analyst", "Executive", "Engineer")),
):
    rows = neo4j_client.top_risks(limit=limit)
    return [
        RiskOut(
            id=r["r"]["id"], title=r["r"]["title"], score=r["r"]["score"],
            likelihood=r["r"]["likelihood"], impact=r["r"]["impact"],
            status=r["r"]["status"], affected_asset_id=r["a"]["id"],
        )
        for r in rows
    ]


@router.get('/assessments')
def asset_assessments(user=Depends(require_role('Admin', 'Analyst', 'Executive', 'Engineer'))):
    from app.services.intelligence import assessments
    return assessments()
