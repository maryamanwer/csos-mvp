"""Orchestration boundary between source adapters, audit history and Neo4j."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors import CollectionResult, get_connector
from app.connectors.base import ConnectorError
from app.core.secrets import decrypt_config
from app.graph.network_writer import network_writer
from app.models.connector import ConnectorConfig, ConnectorRun
from app.services.audit import record_audit

log = logging.getLogger(__name__)


def secret_fields_for(connector_key: str) -> set[str]:
    try:
        connector = get_connector(connector_key)
    except ConnectorError:
        return set()
    return {field.name for field in connector.config_fields if field.secret}


def _complete_run(
    db: Session,
    run: ConnectorRun,
    config: ConnectorConfig,
    result: CollectionResult,
    status: str,
    started: float,
    written: dict[str, int] | None = None,
) -> ConnectorRun:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.duration_seconds = round(time.monotonic() - started, 3)
    counts = result.summary()
    run.assets_found = counts["assets"]
    run.interfaces_found = counts["interfaces"]
    run.links_found = counts["links"]
    run.vulnerabilities_found = counts["vulnerabilities"]
    run.events_found = counts["events"]
    run.written = written or {}
    run.errors = result.errors[:50] or None
    config.last_run_at = run.finished_at
    config.last_run_status = status
    config.last_run_summary = {**counts, "written": written or {}}
    db.commit()
    db.refresh(run)
    return run


def execute_run(
    db: Session,
    config: ConnectorConfig,
    *,
    trigger: str = "manual",
    user_id: uuid.UUID | None = None,
    writer=None,
) -> ConnectorRun:
    started = time.monotonic()
    run = ConnectorRun(
        connector_config_id=config.id,
        connector_key=config.connector_key,
        status="running",
        trigger=trigger,
        triggered_by=user_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    result = CollectionResult(connector_key=config.connector_key)

    try:
        adapter = get_connector(config.connector_key)
        values = decrypt_config(config.config or {}, secret_fields_for(config.connector_key))
        result = adapter.collect(values)
        result.connector_key = config.connector_key
        written = (writer or network_writer).write(result)
        status = "partial" if result.errors else "success"
    except Exception as error:
        log.exception("Collection failed for %s", config.connector_key)
        result.errors.append(str(error))
        written = None
        status = "failed"

    record_audit(
        db,
        "CONNECTOR_RUN" if status != "failed" else "CONNECTOR_RUN_FAILED",
        user_id=user_id,
        entity_type="ConnectorConfig",
        entity_id=str(config.id),
        metadata={"connector": config.connector_key, "trigger": trigger, "status": status, **result.summary()},
    )
    return _complete_run(db, run, config, result, status, started, written)


def ingest_pushed_result(result: CollectionResult, writer=None) -> dict[str, int]:
    return (writer or network_writer).write(result)


def due_configs(db: Session, now: datetime | None = None) -> list[ConnectorConfig]:
    current = now or datetime.now(timezone.utc)
    scheduled = (
        db.query(ConnectorConfig)
        .filter(ConnectorConfig.enabled.is_(True))
        .filter(ConnectorConfig.schedule_minutes.isnot(None))
        .all()
    )
    due: list[ConnectorConfig] = []
    for config in scheduled:
        if not config.schedule_minutes:
            continue
        if config.last_run_at is None:
            due.append(config)
            continue
        previous = config.last_run_at
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
        if (current - previous).total_seconds() >= config.schedule_minutes * 60:
            due.append(config)
    return due
