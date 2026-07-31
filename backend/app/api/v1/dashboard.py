"""Data-backed dashboard summaries for executives and analysts."""
from fastapi import APIRouter, Depends, Query

from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.dashboard import ExecutiveDashboardSummary, InvestigationItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/executive", response_model=ExecutiveDashboardSummary)
def executive_dashboard(
    user: dict = Depends(require_role("Admin", "Executive", "Analyst", "Engineer")),
):
    return neo4j_client.executive_summary()


@router.get("/analyst", response_model=list[InvestigationItem])
def analyst_dashboard(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_role("Admin", "Analyst", "Engineer")),
):
    return neo4j_client.investigation_queue(limit=limit)
