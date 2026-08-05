from pydantic import BaseModel, Field

from app.schemas.risk_compliance import ComplianceFrameworkCoverage, RiskOut


class DistributionItem(BaseModel):
    label: str | None = None
    value: int


class ExecutiveDashboardSummary(BaseModel):
    overall_risk_score: float
    asset_count: int
    open_vulnerability_count: int
    compliance_pct: float
    asset_criticality: list[DistributionItem] = Field(default_factory=list)
    vulnerability_severity: list[DistributionItem] = Field(default_factory=list)
    compliance_frameworks: list[ComplianceFrameworkCoverage] = Field(default_factory=list)
    top_risks: list[RiskOut] = Field(default_factory=list)


class InvestigationItem(BaseModel):
    id: str
    item_type: str
    title: str
    severity: str
    status: str
    priority_score: float
    asset_ids: list[str] = Field(default_factory=list)
    reference: str | None = None
