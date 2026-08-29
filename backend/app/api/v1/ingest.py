"""Write-only authenticated entry points for endpoints and log forwarders."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.connectors.agent_ingest import normalize_agent_payload
from app.connectors.syslog import events_to_result, parse_syslog_line
from app.core.database import get_db
from app.core.secrets import generate_api_key, hash_api_key
from app.core.security import require_role
from app.models.connector import IngestApiKey
from app.schemas.connector import AgentReport, ApiKeyCreate, ApiKeyCreated, ApiKeyOut, IngestResult, SyslogBatch
from app.services.audit import record_audit
from app.services.collection import ingest_pushed_result

router = APIRouter(prefix="/ingest", tags=["ingest"])
log = logging.getLogger(__name__)


def _remote_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _persist(result) -> dict[str, int]:
    try:
        return ingest_pushed_result(result)
    except Exception as error:
        log.error("Push ingestion failed: %s", error)
        raise HTTPException(status_code=503, detail="Graph storage is temporarily unavailable; retry later") from error


def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> IngestApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    item = db.query(IngestApiKey).filter(IngestApiKey.key_hash == hash_api_key(x_api_key)).first()
    now = datetime.now(timezone.utc)
    expired = False
    if item and item.expires_at:
        expires_at = item.expires_at if item.expires_at.tzinfo else item.expires_at.replace(tzinfo=timezone.utc)
        expired = expires_at <= now
    if item is None or not item.enabled or expired:
        raise HTTPException(status_code=401, detail="Invalid API key")
    item.last_used_at = now
    item.last_used_ip = _remote_ip(request)
    item.use_count = (item.use_count or 0) + 1
    db.commit()
    return item


@router.post("/agent", response_model=IngestResult)
def ingest_agent_report(
    report: AgentReport,
    request: Request,
    api_key: IngestApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    if api_key.scope != "agent":
        raise HTTPException(status_code=403, detail="API key scope does not permit endpoint reports")
    result = normalize_agent_payload(report.model_dump())
    if not result.assets:
        return IngestResult(accepted=False, errors=result.errors)
    for asset in result.assets:
        asset.ip_address = asset.ip_address or _remote_ip(request)
    return IngestResult(accepted=True, written=_persist(result), errors=result.errors)


@router.post("/syslog", response_model=IngestResult)
def ingest_syslog_batch(
    batch: SyslogBatch,
    request: Request,
    api_key: IngestApiKey = Depends(verify_api_key),
):
    if api_key.scope != "syslog":
        raise HTTPException(status_code=403, detail="API key scope does not permit Syslog reports")
    source_ip = batch.source_ip or _remote_ip(request)
    result = events_to_result([parse_syslog_line(line, source_ip) for line in batch.lines])
    return IngestResult(accepted=True, written=_persist(result), errors=result.errors)


@router.post("/keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    plaintext = generate_api_key()
    item = IngestApiKey(
        name=payload.name, key_hash=hash_api_key(plaintext), key_prefix=plaintext[:12],
        scope=payload.scope, expires_at=payload.expires_at,
        created_by=uuid.UUID(str(user["id"])),
    )
    db.add(item)
    record_audit(db, "API_KEY_CREATE", user_id=user["id"], entity_type="IngestApiKey", metadata={"name": payload.name, "scope": payload.scope})
    db.commit()
    db.refresh(item)
    return ApiKeyCreated(**ApiKeyOut.model_validate(item).model_dump(), api_key=plaintext)


@router.get("/keys", response_model=list[ApiKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    return db.query(IngestApiKey).order_by(IngestApiKey.created_at.desc()).all()


@router.delete("/keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    item = db.get(IngestApiKey, key_id)
    if item is None:
        raise HTTPException(status_code=404, detail="API key not found")
    item.enabled = False
    record_audit(db, "API_KEY_REVOKE", user_id=user["id"], entity_type="IngestApiKey", entity_id=str(item.id), metadata={"name": item.name})
    db.commit()
