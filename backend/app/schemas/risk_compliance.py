from typing import Optional

from pydantic import BaseModel, Field


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
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    agent_trace: list[str] = Field(default_factory=list)
    conversation_id: str
