"""Push ingestion — endpoints that data sources call, rather than the reverse.

Agents and log forwarders live on machines that may not accept inbound
connections, so they report in. These routes authenticate with an API key
rather than a user session: an agent is not a person, has no role, and must
never be able to read anything back.
"""
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
from app.schemas.connector import (
    AgentReport,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    IngestResult,
    SyslogBatch,
)
from app.services.audit import record_audit
from app.services.collection import ingest_pushed_result

router = APIRouter(prefix="/ingest", tags=["ingest"])


logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _write_or_503(result) -> dict[str, int]:
    """Persist a pushed result, translating a graph outage into a clear 503.

    Agents run unattended on hundreds of machines. A generic 500 tells their
    operator nothing and is indistinguishable from a bad payload, so a storage
    outage is reported as retryable with a message that names the cause.
    """
    try:
        return ingest_pushed_result(result)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unable to persist pushed data in the graph: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "The graph database is unavailable and the payload was not saved. "
                "Retry the request later."
            ),
        ) from exc


def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> IngestApiKey:
    """Authenticate a push source by its API key.

    Lookup is by hash, so the database never holds a usable credential. The
    same generic message is returned for missing, unknown, disabled and expired
    keys — an unauthenticated caller learns nothing about which it was.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key = (
        db.query(IngestApiKey)
        .filter(IngestApiKey.key_hash == hash_api_key(x_api_key))
        .first()
    )
    if key is None or not key.enabled:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if key.expires_at is not None:
        expires = key.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Invalid API key")

    key.last_used_at = datetime.now(timezone.utc)
    key.last_used_ip = _client_ip(request)
    key.use_count = (key.use_count or 0) + 1
    db.commit()
    return key


@router.post("/agent", response_model=IngestResult)
def ingest_agent_report(
    report: AgentReport,
    request: Request,
    api_key: IngestApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Receive one inventory report from an endpoint agent."""
    if api_key.scope != "agent":
        raise HTTPException(status_code=403, detail="API key scope does not permit agent reports")

    result = normalize_agent_payload(report.model_dump())
    if result.errors and not result.assets:
        return IngestResult(accepted=False, errors=result.errors)

    # An agent reports its own hostname; record where the report actually came
    # from so a spoofed hostname is still traceable to a source address.
    source_ip = _client_ip(request)
    for asset in result.assets:
        if not asset.ip_address:
            asset.ip_address = source_ip

    written = _write_or_503(result)
    return IngestResult(accepted=True, written=written, errors=result.errors)


@router.post("/syslog", response_model=IngestResult)
def ingest_syslog_batch(
    batch: SyslogBatch,
    request: Request,
    api_key: IngestApiKey = Depends(verify_api_key),
):
    """Accept syslog lines over HTTP.

    The UDP and TCP listeners are the normal path; this exists for segments
    where only HTTPS is permitted through the firewall.
    """
    source_ip = batch.source_ip or _client_ip(request)
    events = [parse_syslog_line(line, source_ip) for line in batch.lines]
    result = events_to_result([event for event in events if event.message])
    written = _write_or_503(result)
    return IngestResult(accepted=True, written=written, errors=result.errors)


# --- API key administration -------------------------------------------

@router.post("/keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    """Issue an enrolment key. The plaintext is shown here and never again."""
    plaintext = generate_api_key()
    key = IngestApiKey(
        name=payload.name,
        key_hash=hash_api_key(plaintext),
        key_prefix=plaintext[:12],
        scope=payload.scope,
        expires_at=payload.expires_at,
        created_by=uuid.UUID(str(user["id"])),
    )
    db.add(key)
    record_audit(
        db,
        "API_KEY_CREATE",
        user_id=user["id"],
        entity_type="IngestApiKey",
        metadata={"name": payload.name, "scope": payload.scope},
    )
    db.commit()
    db.refresh(key)

    # Built field by field rather than validated from the ORM object: the
    # plaintext key exists only in this scope and is deliberately not a column.
    return ApiKeyCreated(
        **ApiKeyOut.model_validate(key).model_dump(),
        api_key=plaintext,
    )


@router.get("/keys", response_model=list[ApiKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    keys = db.query(IngestApiKey).order_by(IngestApiKey.created_at.desc()).all()
    return [ApiKeyOut.model_validate(key) for key in keys]


@router.delete("/keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("Admin")),
):
    """Disable rather than delete, so the audit trail keeps its references."""
    key = db.get(IngestApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    key.enabled = False
    record_audit(
        db,
        "API_KEY_REVOKE",
        user_id=user["id"],
        entity_type="IngestApiKey",
        entity_id=str(key.id),
        metadata={"name": key.name},
    )
    db.commit()
