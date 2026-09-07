"""
Risk Engine endpoints using one explainable calculated score across risk views.
"""
from fastapi import APIRouter, Depends, Query

from app.core.security import require_permission
from app.graph.neo4j_client import neo4j_client
from app.schemas.risk_compliance import RiskOut

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/top", response_model=list[RiskOut])
def top_risks(
    limit: int = Query(5, ge=1, le=1000),
    user: dict = Depends(require_permission("risk:read")),
):
    from app.services.intelligence import assessments
    return [
        RiskOut(id=f"assessment-{r['affected_asset_id']}", title=r["title"], score=r["score"],
                likelihood=r["likelihood"], impact=r["impact"], status="open",
                affected_asset_id=r["affected_asset_id"])
        for r in assessments()[:limit]
    ]


@router.get('/assessments')
def asset_assessments(user=Depends(require_permission('risk:read'))):
    from app.services.intelligence import assessments
    return assessments()
