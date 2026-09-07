"""Data-backed dashboard summaries for executives and analysts."""
from fastapi import APIRouter, Depends, Query

from app.core.security import require_permission
from app.graph.neo4j_client import neo4j_client
from app.schemas.dashboard import ExecutiveDashboardSummary, InvestigationItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/executive", response_model=ExecutiveDashboardSummary)
def executive_dashboard(
    user: dict = Depends(require_permission("dashboard:read")),
):
    from app.services.intelligence import assessments
    summary = neo4j_client.executive_summary()
    calculated = assessments()
    summary["overall_risk_score"] = round(
        sum(item["score"] for item in calculated) / len(calculated), 1
    ) if calculated else 0
    summary["top_risks"] = [
        {"id": f"assessment-{item['affected_asset_id']}", "title": item["title"],
         "score": item["score"], "likelihood": item["likelihood"],
         "impact": item["impact"], "status": "open",
         "affected_asset_id": item["affected_asset_id"]}
        for item in calculated[:5]
    ]
    return summary


@router.get("/analyst", response_model=list[InvestigationItem])
def analyst_dashboard(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_permission("dashboard:read")),
):
    return neo4j_client.investigation_queue(limit=limit)
