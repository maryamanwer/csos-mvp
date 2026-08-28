"""Collection layer API — configure sources, run them, review what they did."""
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
    ConnectionTestResult,
    ConnectorConfigCreate,
    ConnectorConfigOut,
    ConnectorConfigUpdate,
    ConnectorRunOut,
    ConnectorTypeOut,
)
from app.services.audit import record_audit
from app.services.collection import execute_run, secret_fields_for

router = APIRouter(prefix="/connectors", tags=["connectors"])

MANAGE_ROLES = ("Admin", "Engineer")
VIEW_ROLES = ("Admin", "Engineer", "Analyst", "Executive", "ComplianceOfficer")


def _to_out(config: ConnectorConfig) -> ConnectorConfigOut:
    """Never return a stored secret, even to an administrator."""
    payload = ConnectorConfigOut.model_validate(config)
    payload.config = redact_config(
        config.config or {}, secret_fields_for(config.connector_key)
    )
    return payload


def _get_or_404(db: Session, config_id: uuid.UUID) -> ConnectorConfig:
    config = db.get(ConnectorConfig, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connector configuration not found")
    return config


@router.get("/types", response_model=list[ConnectorTypeOut])
def available_connector_types(user: dict = Depends(require_role(*VIEW_ROLES))):
    """Every connector the platform can run, with the fields each one needs.

    The UI renders configuration forms from this, so a connector added later
    needs no front-end change to become configurable.
    """
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
    return [
        _to_out(config)
        for config in query.order_by(ConnectorConfig.created_at.desc()).all()
    ]


@router.post("", response_model=ConnectorConfigOut, status_code=201)
def create_connector_config(
    payload: ConnectorConfigCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    try:
        connector = get_connector(payload.connector_key)
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    merged = connector.apply_defaults(payload.config)
    try:
        connector.validate_config(merged)
    except ConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if payload.schedule_minutes and not connector.schedulable:
        raise HTTPException(
            status_code=422,
            detail=f"Connector '{payload.connector_key}' is push-based and cannot be scheduled",
        )

    config = ConnectorConfig(
        name=payload.name,
        connector_key=payload.connector_key,
        description=payload.description,
        config=encrypt_config(merged, secret_fields_for(payload.connector_key)),
        enabled=payload.enabled,
        schedule_minutes=payload.schedule_minutes,
        created_by=uuid.UUID(str(user["id"])),
    )
    db.add(config)
    record_audit(
        db,
        "CONNECTOR_CREATE",
        user_id=user["id"],
        entity_type="ConnectorConfig",
        metadata={"connector": payload.connector_key, "name": payload.name},
    )
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.get("/runs/recent", response_model=list[ConnectorRunOut])
def recent_runs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*VIEW_ROLES)),
):
    """Latest activity across every source: the collection layer's pulse."""
    runs = (
        db.query(ConnectorRun)
        .order_by(ConnectorRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [ConnectorRunOut.model_validate(run) for run in runs]


@router.patch("/{config_id}", response_model=ConnectorConfigOut)
def update_connector_config(
    config_id: uuid.UUID,
    payload: ConnectorConfigUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    config = _get_or_404(db, config_id)
    secret_fields = secret_fields_for(config.connector_key)

    if payload.config is not None:
        # A redacted secret coming back from the UI means "unchanged" — never
        # overwrite a stored credential with the mask.
        existing = decrypt_config(config.config or {}, secret_fields)
        merged = {**existing}
        for key, value in payload.config.items():
            if key in secret_fields and value == "••••••••":
                continue
            merged[key] = value
        try:
            get_connector(config.connector_key).validate_config(merged)
        except ConfigurationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except ConnectorError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        config.config = encrypt_config(merged, secret_fields)

    explicitly_set = payload.model_fields_set
    for field in ("name", "description", "enabled", "schedule_minutes"):
        value = getattr(payload, field)
        if value is not None or field in explicitly_set:
            setattr(config, field, value)

    record_audit(
        db,
        "CONNECTOR_UPDATE",
        user_id=user["id"],
        entity_type="ConnectorConfig",
        entity_id=str(config.id),
        metadata={"connector": config.connector_key},
    )
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.delete("/{config_id}", status_code=204)
def delete_connector_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    config = _get_or_404(db, config_id)
    record_audit(
        db,
        "CONNECTOR_DELETE",
        user_id=user["id"],
        entity_type="ConnectorConfig",
        entity_id=str(config.id),
        metadata={"connector": config.connector_key, "name": config.name},
    )
    db.delete(config)
    db.commit()


@router.post("/{config_id}/test", response_model=ConnectionTestResult)
def test_connector_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    """Verify credentials and reachability without ingesting anything."""
    config = _get_or_404(db, config_id)
    try:
        connector = get_connector(config.connector_key)
        plain = decrypt_config(
            config.config or {}, secret_fields_for(config.connector_key)
        )
        success, message = connector.test_connection(plain)
    except ConnectorError as exc:
        return ConnectionTestResult(success=False, message=str(exc))
    return ConnectionTestResult(success=success, message=message)


@router.post("/{config_id}/run", response_model=ConnectorRunOut)
def run_connector(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGE_ROLES)),
):
    """Collect now, synchronously, and return the run record."""
    config = _get_or_404(db, config_id)
    if not config.enabled:
        raise HTTPException(status_code=409, detail="Connector is disabled")
    run = execute_run(db, config, trigger="manual", user_id=uuid.UUID(str(user["id"])))
    return ConnectorRunOut.model_validate(run)


@router.get("/{config_id}/runs", response_model=list[ConnectorRunOut])
def connector_run_history(
    config_id: uuid.UUID,
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*VIEW_ROLES)),
):
    _get_or_404(db, config_id)
    runs = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.connector_config_id == config_id)
        .order_by(ConnectorRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [ConnectorRunOut.model_validate(run) for run in runs]
