from datetime import datetime
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
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    agent_trace: list[str] = Field(default_factory=list)
    conversation_id: str
    citations: list[dict[str, str]] = Field(default_factory=list)


class ChatConversationOut(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChatMessageOut(BaseModel):
    role: str
    content: str
    agent_trace: list[str] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime | None = None
