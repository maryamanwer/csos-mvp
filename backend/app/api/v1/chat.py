"""User-facing endpoint for the grounded LangGraph orchestrator."""
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.agents.orchestrator import run_orchestrator
from app.models.ai import AIConversation, AIMessage
from app.schemas.risk_compliance import (
    ChatConversationOut,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _chat(
    payload: ChatRequest,
    user: dict,
    db: Session,
) -> ChatResponse:
    user_id = uuid.UUID(str(user["id"]))
    conversation: AIConversation | None = None
    if payload.conversation_id:
        try:
            conversation_id = uuid.UUID(payload.conversation_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid conversation ID") from exc
        conversation = (
            db.query(AIConversation)
            .filter(AIConversation.id == conversation_id, AIConversation.user_id == user_id)
            .first()
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = AIConversation(
            user_id=user_id,
            title=payload.message.strip()[:120],
        )
        db.add(conversation)
        db.flush()

    history_rows = (
        db.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history = [
        {"role": row.role, "content": row.content}
        for row in reversed(history_rows)
    ]
    result = run_orchestrator(
        payload.message,
        user_role=user["role"],
        conversation_history=history,
    )
    response = ChatResponse(
        reply=result.get("final_reply", "No grounded response was produced."),
        agent_trace=result.get("agent_trace", []),
        citations=result.get("citations", []),
        conversation_id=str(conversation.id),
    )
    db.add(AIMessage(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    ))
    db.add(AIMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response.reply,
        agent_trace=response.agent_trace,
        citations=response.citations,
    ))
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return response


@router.get("/conversations", response_model=list[ChatConversationOut])
def list_conversations(
    limit: int = 25,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = uuid.UUID(str(user["id"]))
    rows = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == user_id)
        .order_by(AIConversation.updated_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [
        ChatConversationOut(
            id=str(row.id), title=row.title,
            created_at=row.created_at, updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ChatMessageOut],
)
def conversation_messages(
    conversation_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = uuid.UUID(str(user["id"]))
    conversation = (
        db.query(AIConversation)
        .filter(AIConversation.id == conversation_id, AIConversation.user_id == user_id)
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = (
        db.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at.asc())
        .limit(200)
        .all()
    )
    return [
        ChatMessageOut(
            role=row.role,
            content=row.content,
            agent_trace=row.agent_trace or [],
            citations=row.citations or [],
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/stream")
def stream_chat(
    payload: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = _chat(payload, user, db)

    def events():
        for token in response.reply.split():
            yield f"data: {json.dumps({'type': 'token', 'content': token + ' '})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', **response.model_dump()})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _chat(payload, user, db)
