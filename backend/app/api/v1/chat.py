import uuid
import httpx
import ollama
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.schemas.risk_compliance import ChatRequest
from app.agents.orchestrator import run_orchestrator
from app.ai.providers import resolve_model, ModelSelectionError

router = APIRouter(prefix='/chat', tags=['chat'])

@router.post('')
def chat(payload: ChatRequest, user=Depends(get_current_user), db: Session=Depends(get_db)):
    if not payload.message.strip(): raise HTTPException(422, 'Message must not be blank')
    try: resolve_model(payload.model)
    except ModelSelectionError as exc: raise HTTPException(422, str(exc))
    conversation = None
    if payload.conversation_id:
        try: cid = uuid.UUID(payload.conversation_id)
        except ValueError: raise HTTPException(422, 'Invalid conversation ID')
        conversation = db.query(Conversation).filter_by(id=cid, user_id=uuid.UUID(user['id'])).with_for_update().first()
        if conversation is None: raise HTTPException(404, 'Conversation not found')
    else:
        conversation = Conversation(user_id=uuid.UUID(user['id']), messages=[])
        db.add(conversation)
    history = [m for m in conversation.messages if m.get('access_role') == user['role']]
    try:
        result = run_orchestrator(payload.message, user['role'], history[-12:], payload.model)
    except (httpx.HTTPError, ollama.ResponseError, ConnectionError):
        db.rollback()
        raise HTTPException(503, 'AI runtime unavailable. Check Ollama and install an enabled model.')
    conversation.messages = [*history[-38:], {'role': 'user', 'content': payload.message, 'access_role': user['role']},
                             {'role': 'assistant', 'content': result['final_reply'], 'access_role': user['role']}]
    db.commit()
    return {'reply': result['final_reply'], 'agent_trace': result['agent_trace'],
            'citations': result.get('citations', []), 'conversation_id': str(conversation.id)}
