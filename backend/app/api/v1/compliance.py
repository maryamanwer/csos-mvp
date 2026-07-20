"""
Compliance Engine endpoints (MVP implementation).
TODO(M4): compute real coverage_pct from Control/Framework graph relationships.
"""
from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.schemas.risk_compliance import ComplianceFrameworkCoverage

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/coverage", response_model=list[ComplianceFrameworkCoverage])
def framework_coverage(user: dict = Depends(require_role("Admin", "ComplianceOfficer", "Executive"))):
    # TODO(M4): replace with real Neo4j aggregation:
    # MATCH (c:Control)-[:PART_OF]->(f:Framework) ... count met vs total
    return [
        ComplianceFrameworkCoverage(framework="ISO 27001", total_controls=93, controls_met=61, coverage_pct=65.6),
        ComplianceFrameworkCoverage(framework="NIST CSF", total_controls=108, controls_met=70, coverage_pct=64.8),
    ]
