"""Runs connectors and records what each run did.

Every path into the graph goes through :func:`execute_run` — manual triggers,
the scheduler, and push endpoints alike. That single choke point is what makes
ingestion auditable: nothing reaches the Knowledge Graph without a
``ConnectorRun`` row saying which connector produced it, when, and with what
outcome.
"""
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

logger = logging.getLogger(__name__)


def secret_fields_for(connector_key: str) -> set[str]:
    """Which configuration fields of this connector hold secrets."""
    try:
        connector = get_connector(connector_key)
    except ConnectorError:
        return set()
    return {field.name for field in connector.config_fields if field.secret}


def _finish(
    db: Session,
    run: ConnectorRun,
    status: str,
    result: CollectionResult,
    written: dict[str, int] | None,
    started: float,
) -> ConnectorRun:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.duration_seconds = round(time.monotonic() - started, 3)
    run.assets_found = len(result.assets)
    run.interfaces_found = len(result.interfaces)
    run.links_found = len(result.links)
    run.vulnerabilities_found = len(result.vulnerabilities)
    run.events_found = len(result.events)
    run.written = written or {}
    run.errors = result.errors[:50] or None

    config = db.get(ConnectorConfig, run.connector_config_id)
    if config is not None:
        config.last_run_at = run.finished_at
        config.last_run_status = status
        config.last_run_summary = {**result.summary(), "written": written or {}}

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
    """Collect from one configured source and persist the result.

    A device that cannot be reached is an error inside the result, not an
    exception — the run is then marked ``partial`` and whatever *was* collected
    still lands. Only a total failure marks the run ``failed``.
    """
    writer = writer or network_writer
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
        connector = get_connector(config.connector_key)
        plain_config = decrypt_config(
            config.config or {}, secret_fields_for(config.connector_key)
        )
        result = connector.collect(plain_config)
        result.connector_key = config.connector_key
    except Exception as exc:  # noqa: BLE001 - a failed run must still be recorded
        logger.exception("Connector %s failed", config.connector_key)
        result.errors.append(str(exc))
        record_audit(
            db,
            "CONNECTOR_RUN_FAILED",
            user_id=user_id,
            entity_type="ConnectorConfig",
            entity_id=str(config.id),
            metadata={"connector": config.connector_key, "error": str(exc)[:500]},
        )
        return _finish(db, run, "failed", result, None, started)

    try:
        written = writer.write(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unable to write %s collection result to the graph", config.connector_key)
        result.errors.append(f"Graph write failed: {exc}")
        return _finish(db, run, "failed", result, None, started)

    status = "partial" if result.errors else "success"
    record_audit(
        db,
        "CONNECTOR_RUN",
        user_id=user_id,
        entity_type="ConnectorConfig",
        entity_id=str(config.id),
        metadata={
            "connector": config.connector_key,
            "trigger": trigger,
            "status": status,
            **result.summary(),
        },
    )
    return _finish(db, run, status, result, written, started)


def ingest_pushed_result(
    result: CollectionResult, writer=None
) -> dict[str, int]:
    """Write a push-sourced result (agent, syslog) straight to the graph.

    Push sources have no ``ConnectorConfig`` to schedule, so they bypass run
    history; their audit trail is the API key usage record instead.
    """
    writer = writer or network_writer
    return writer.write(result)


def due_configs(db: Session, now: datetime | None = None) -> list[ConnectorConfig]:
    """Configurations whose schedule interval has elapsed."""
    now = now or datetime.now(timezone.utc)
    candidates = (
        db.query(ConnectorConfig)
        .filter(ConnectorConfig.enabled.is_(True))
        .filter(ConnectorConfig.schedule_minutes.isnot(None))
        .all()
    )

    due: list[ConnectorConfig] = []
    for config in candidates:
        interval = config.schedule_minutes or 0
        if interval <= 0:
            continue
        if config.last_run_at is None:
            due.append(config)
            continue
        last = config.last_run_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() >= interval * 60:
            due.append(config)
    return due
