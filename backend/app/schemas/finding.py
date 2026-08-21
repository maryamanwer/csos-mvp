from typing import Any, Literal

from pydantic import BaseModel, Field


FindingStatus = Literal["open", "in_progress", "resolved", "accepted_risk"]
RiskLevel = Literal["low", "medium", "high"]


class SecurityFinding(BaseModel):
    finding_id: str
    cve_id: str | None = None
    title: str
    asset_id: str
    asset_name: str
    preferred_hostname: str | None = None
    asset_type: str
    asset_criticality: str
    asset_owner: str | None = None
    ip_address: str | None = None
    operating_system: str | None = None
    edr_status: str
    edr_product: str | None = None
    severity: str
    cvss_score: float
    risk_score: float
    risk_level: RiskLevel
    status: FindingStatus
    first_detected: str | None = None
    last_seen: str | None = None
    sla_due_at: str | None = None
    sla_status: str
    sla_days_remaining: int | None = None
    data_sources: list[str] = Field(default_factory=list)
    recommended_remediation: str | None = None
    controls: list[dict[str, Any]] = Field(default_factory=list)


class FindingsSummary(BaseModel):
    total_findings: int = 0
    critical_findings: int = 0
    sla_breaches: int = 0
    critical_assets_without_edr: int = 0
    critical_vulnerabilities_on_critical_assets: int = 0
    outdated_security_agents: int = 0
    assets_missing_controls: int = 0
    unmanaged_assets: int = 0


class SecurityFindingsPage(BaseModel):
    items: list[SecurityFinding] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    summary: FindingsSummary


class FindingDetail(BaseModel):
    finding: SecurityFinding
    asset: dict[str, Any]
    owner_identities: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)
    connected_assets: list[dict[str, Any]] = Field(default_factory=list)
    relationship_chain: list[dict[str, str]] = Field(default_factory=list)
