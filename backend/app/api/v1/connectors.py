"""Authenticated management API for CSOS data sources."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.connectors import get_connector, list_connectors
from app.connectors.base import ConfigurationError, ConnectorError
from app.core.database import get_db
from app.core.security import require_role
from app.core.secrets import decrypt_config, encrypt_config, redact_config
from app.models.connector import ConnectorConfig, ConnectorRun
from app.schemas.connector import (
    ConnectionTestResult, ConnectorConfigCreate, ConnectorConfigOut, ConnectorConfigUpdate,
    ConnectorRunOut, ConnectorTypeOut,
)
from app.services.audit import record_audit
from app.services.collection import execute_run, secret_fields_for

router = APIRouter(prefix="/connectors", tags=["connectors"])
MANAGE_ROLES = ("Admin", "Engineer")
VIEW_ROLES = ("Admin", "Engineer", "Analyst", "Executive", "ComplianceOfficer")
_MASK = "••••••••"


def _lookup(db: Session, connector_id: uuid.UUID) -> ConnectorConfig:
    item = db.get(ConnectorConfig, connector_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Connector configuration not found")
    return item


def _response(item: ConnectorConfig) -> ConnectorConfigOut:
    output = ConnectorConfigOut.model_validate(item)
    output.config = redact_config(item.config or {}, secret_fields_for(item.connector_key))
    return output


def _adapter(key: str):
    try:
        return get_connector(key)
    except ConnectorError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _validated(adapter, values: dict) -> dict:
    ready = adapter.apply_defaults(values)
    try:
        adapter.validate_config(ready)
    except ConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ready


@router.get("/types", response_model=list[ConnectorTypeOut])
def available_connector_types(user: dict = Depends(require_role(*VIEW_ROLES))):
    return list_connectors()


@router.get("", response_model=list[ConnectorConfigOut])
def list_connector_configs(
    connector_key: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*VIEW_ROLES)),
):
    query = db.query(ConnectorConfig)
    if connector_key:
        query = query.filter(ConnectorConfig.connector_key == connector_key)
    if enabled is not None:
        query = query.filter(ConnectorConfig.enabled.is_(enabled))
    return [_response(item) for item in query.order_by(ConnectorConfig.created_at.desc()).all()]


@router.post("", response_model=ConnectorConfigOut, status_code=201)
def create_connector_config(
    payload: ConnectorConfigCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    adapter = _adapter(payload.connector_key)
    values = _validated(adapter, payload.config)
    if payload.schedule_minutes and not adapter.schedulable:
        raise HTTPException(status_code=422, detail="Push-based connectors cannot be scheduled")
    item = ConnectorConfig(
        name=payload.name, connector_key=payload.connector_key,
        description=payload.description,
        config=encrypt_config(values, secret_fields_for(payload.connector_key)),
        enabled=payload.enabled, schedule_minutes=payload.schedule_minutes,
        created_by=uuid.UUID(str(user["id"])),
    )
    db.add(item)
    record_audit(db, "CONNECTOR_CREATE", user_id=user["id"], entity_type="ConnectorConfig", metadata={"connector": payload.connector_key, "name": payload.name})
    db.commit()
    db.refresh(item)
    return _response(item)


@router.get("/runs/recent", response_model=list[ConnectorRunOut])
def recent_runs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*VIEW_ROLES)),
):
    return db.query(ConnectorRun).order_by(ConnectorRun.started_at.desc()).limit(limit).all()


@router.patch("/{config_id}", response_model=ConnectorConfigOut)
def update_connector_config(
    config_id: uuid.UUID,
    payload: ConnectorConfigUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    item = _lookup(db, config_id)
    adapter = _adapter(item.connector_key)
    secret_fields = secret_fields_for(item.connector_key)
    if payload.config is not None:
        values = decrypt_config(item.config or {}, secret_fields)
        values.update({key: value for key, value in payload.config.items() if not (key in secret_fields and value == _MASK)})
        item.config = encrypt_config(_validated(adapter, values), secret_fields)
    if payload.schedule_minutes and not adapter.schedulable:
        raise HTTPException(status_code=422, detail="Push-based connectors cannot be scheduled")
    for field in ("name", "description", "enabled", "schedule_minutes"):
        if field in payload.model_fields_set:
            setattr(item, field, getattr(payload, field))
    record_audit(db, "CONNECTOR_UPDATE", user_id=user["id"], entity_type="ConnectorConfig", entity_id=str(item.id), metadata={"connector": item.connector_key})
    db.commit()
    db.refresh(item)
    return _response(item)


@router.delete("/{config_id}", status_code=204)
def delete_connector_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    item = _lookup(db, config_id)
    record_audit(db, "CONNECTOR_DELETE", user_id=user["id"], entity_type="ConnectorConfig", entity_id=str(item.id), metadata={"connector": item.connector_key})
    db.delete(item)
    db.commit()


@router.post("/{config_id}/test", response_model=ConnectionTestResult)
def test_connector_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    item = _lookup(db, config_id)
    try:
        values = decrypt_config(item.config or {}, secret_fields_for(item.connector_key))
        success, message = _adapter(item.connector_key).test_connection(values)
    except ConnectorError as error:
        success, message = False, str(error)
    return ConnectionTestResult(success=success, message=message)


@router.post("/{config_id}/run", response_model=ConnectorRunOut)
def run_connector(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    item = _lookup(db, config_id)
    if not item.enabled:
        raise HTTPException(status_code=409, detail="Connector is disabled")
    return execute_run(db, item, user_id=uuid.UUID(str(user["id"])))


@router.get("/{config_id}/runs", response_model=list[ConnectorRunOut])
def connector_run_history(
    config_id: uuid.UUID,
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*VIEW_ROLES)),
):
    _lookup(db, config_id)
    return (
        db.query(ConnectorRun)
        .filter(ConnectorRun.connector_config_id == config_id)
        .order_by(ConnectorRun.started_at.desc())
        .limit(limit).all()
    )
