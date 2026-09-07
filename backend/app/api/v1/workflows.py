import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_permission, get_current_user
from app.models.workflow import Workflow
from app.models.audit import Notification
from app.graph.neo4j_client import neo4j_client
from app.services.audit import record_audit
router = APIRouter(tags=['workflows'])
editor = require_permission('workflow:manage')
class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    asset_id: str | None = Field(None, max_length=100)
class Transition(BaseModel):
    status: Literal['open', 'in_progress', 'resolved', 'closed']
    expected_status: Literal['open', 'in_progress', 'resolved', 'closed']
def describe(item):
    return {'id': str(item.id), 'title': item.title, 'asset_id': item.asset_id, 'status': item.status}
@router.get('/workflows')
def tasks(user=Depends(editor), db: Session=Depends(get_db)):
    return [describe(t) for t in db.query(Workflow).filter_by(owner_id=uuid.UUID(user['id'])).order_by(Workflow.created_at.desc()).limit(1000)]
@router.post('/workflows', status_code=201)
def create(payload: TaskInput, user=Depends(editor), db: Session=Depends(get_db)):
    if not payload.title.strip(): raise HTTPException(422, 'Title cannot be blank')
    if payload.asset_id and not neo4j_client.get_asset(payload.asset_id): raise HTTPException(422, 'Asset not found')
    item = Workflow(title=payload.title.strip(), asset_id=payload.asset_id, owner_id=uuid.UUID(user['id']))
    db.add(item); db.flush()
    record_audit(db, 'WORKFLOW_CREATED', user['id'], 'workflow', str(item.id))
    db.commit()
    return describe(item)
@router.patch('/workflows/{task_id}')
def transition(task_id: uuid.UUID, payload: Transition, user=Depends(editor), db: Session=Depends(get_db)):
    item = db.query(Workflow).filter_by(id=task_id, owner_id=uuid.UUID(user['id'])).with_for_update().first()
    if not item: raise HTTPException(404, 'Task not found')
    allowed = {'open': ['in_progress'], 'in_progress': ['open','resolved'], 'resolved': ['in_progress','closed'], 'closed': ['open']}
    if payload.expected_status != item.status: raise HTTPException(409, 'Task changed; reload before updating')
    if payload.status not in allowed[item.status]: raise HTTPException(409, 'Invalid workflow transition')
    before = item.status
    item.status = payload.status
    db.add(Notification(user_id=item.owner_id, title='Workflow updated', body=f'{item.title}: {before} → {item.status}', severity='info'))
    record_audit(db, 'WORKFLOW_TRANSITION', user['id'], 'workflow', str(item.id), {'from': before, 'to': item.status})
    db.commit()
    return describe(item)
@router.get('/notifications')
def notifications(user=Depends(get_current_user), db: Session=Depends(get_db)):
    return [{'id': str(n.id), 'title': n.title, 'body': n.body, 'read': n.read} for n in
            db.query(Notification).filter_by(user_id=uuid.UUID(user['id'])).order_by(Notification.created_at.desc()).limit(100)]
@router.patch('/notifications/{notification_id}/read')
def mark_read(notification_id: uuid.UUID, user=Depends(get_current_user), db: Session=Depends(get_db)):
    item = db.query(Notification).filter_by(id=notification_id, user_id=uuid.UUID(user['id'])).first()
    if not item: raise HTTPException(404, 'Notification not found')
    item.read = True; db.commit()
    return {'read': True}
