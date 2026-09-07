from fastapi import APIRouter, Depends, Query
from app.core.security import require_role
from app.schemas.risk_compliance import ComplianceFrameworkCoverage
from app.services.intelligence import coverage, gaps
router = APIRouter(prefix='/compliance', tags=['compliance'])
reader = require_role('Admin', 'ComplianceOfficer', 'Executive')
@router.get('/coverage', response_model=list[ComplianceFrameworkCoverage])
def framework_coverage(user=Depends(reader)):
    return coverage()
@router.get('/gaps')
def control_gaps(framework: str | None = Query(None, max_length=255), user=Depends(reader)):
    return gaps(framework)
