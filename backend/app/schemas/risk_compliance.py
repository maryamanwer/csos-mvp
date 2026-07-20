from typing import Optional

from pydantic import BaseModel


class RiskOut(BaseModel):
    id: str
    title: str
    score: float
    likelihood: str
    impact: str
    status: str
    affected_asset_id: Optional[str] = None


class ComplianceFrameworkCoverage(BaseModel):
    framework: str
    total_controls: int
    controls_met: int
    coverage_pct: float


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    agent_trace: list[str] = []
    conversation_id: str
