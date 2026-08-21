"""Correlated security findings across assets, vulnerabilities, risks, and controls."""
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.finding import FindingDetail, FindingsSummary, SecurityFindingsPage

router = APIRouter(prefix="/findings", tags=["security-findings"])
READ_ROLES = ("Admin", "Engineer", "Analyst", "Executive", "ComplianceOfficer")


def _filters(
    search: str | None,
    risk_level: str | None,
    criticality: str | None,
    severity: str | None,
    edr_coverage: str | None,
    asset_type: str | None,
    owner: str | None,
    status: str | None,
    data_source: str | None,
) -> dict:
    return {
        "search": search,
        "risk_level": risk_level,
        "criticality": criticality,
        "severity": severity,
        "edr_coverage": edr_coverage,
        "asset_type": asset_type,
        "owner": owner,
        "status": status,
        "data_source": data_source,
    }


@router.get("", response_model=SecurityFindingsPage)
def list_findings(
    search: str | None = Query(default=None, max_length=120),
    risk_level: str | None = Query(default=None),
    criticality: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    edr_coverage: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    owner: str | None = Query(default=None, max_length=255),
    status: str | None = Query(default=None),
    data_source: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(default="risk_score", max_length=50),
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=10, le=200),
    user: dict = Depends(require_role(*READ_ROLES)),
):
    result = neo4j_client.list_security_findings(
        **_filters(
            search,
            risk_level,
            criticality,
            severity,
            edr_coverage,
            asset_type,
            owner,
            status,
            data_source,
        ),
        sort_by=sort_by,
        sort_direction=sort_direction,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return {
        **result,
        "page": page,
        "page_size": page_size,
        "summary": neo4j_client.findings_summary(),
    }


@router.get("/summary", response_model=FindingsSummary)
def findings_summary(user: dict = Depends(require_role(*READ_ROLES))):
    return neo4j_client.findings_summary()


@router.get("/export")
def export_findings(
    search: str | None = Query(default=None, max_length=120),
    risk_level: str | None = Query(default=None),
    criticality: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    edr_coverage: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    owner: str | None = Query(default=None, max_length=255),
    status: str | None = Query(default=None),
    data_source: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(default="risk_score", max_length=50),
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: dict = Depends(require_role(*READ_ROLES)),
):
    result = neo4j_client.list_security_findings(
        **_filters(
            search,
            risk_level,
            criticality,
            severity,
            edr_coverage,
            asset_type,
            owner,
            status,
            data_source,
        ),
        sort_by=sort_by,
        sort_direction=sort_direction,
        offset=0,
        limit=5000,
    )
    columns = [
        "finding_id",
        "cve_id",
        "asset_name",
        "preferred_hostname",
        "asset_type",
        "asset_criticality",
        "asset_owner",
        "ip_address",
        "operating_system",
        "edr_status",
        "edr_product",
        "severity",
        "cvss_score",
        "risk_score",
        "risk_level",
        "status",
        "first_detected",
        "last_seen",
        "sla_due_at",
        "sla_status",
        "data_sources",
        "recommended_remediation",
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for item in result["items"]:
        writer.writerow({**item, "data_sources": "; ".join(item["data_sources"])})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=csos-security-findings.csv"},
    )


@router.get("/{finding_id}", response_model=FindingDetail)
def get_finding(
    finding_id: str,
    asset_id: str | None = Query(default=None),
    user: dict = Depends(require_role(*READ_ROLES)),
):
    finding = neo4j_client.get_security_finding(finding_id, asset_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Security finding not found")
    return finding
