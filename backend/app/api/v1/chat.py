"""
AI Chat Assistant endpoint — the user-facing entry point into the
LangGraph multi-agent orchestrator.
TODO(M3): replace the stubbed reply with a call into
app/agents/orchestrator.py's compiled LangGraph app.
"""
import uuid

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.risk_compliance import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: dict = Depends(get_current_user)):
    # TODO(M3):
    # from app.agents.orchestrator import run_orchestrator
    # result = run_orchestrator(payload.message, user_role=user["role"])
    return ChatResponse(
        reply=(
            "AI Chat Assistant is not yet wired to the LangGraph orchestrator "
            "(Milestone 3). This is a stubbed response."
        ),
        agent_trace=["orchestrator (stub)"],
        conversation_id=payload.conversation_id or str(uuid.uuid4()),
    )
