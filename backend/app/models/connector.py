"""Relational records for the collection layer.

Connector *configuration* is relational: it is small, transactional, and needs
referential integrity with users and audit. Collected *data* is graph, because
that is where relationships matter. Keeping the split explicit is what lets the
graph stay a clean model of the estate rather than a settings store.
"""
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)

from app.core.database import Base


class ConnectorConfig(Base):
    """One configured instance of a connector — e.g. 'core switches over SSH'."""

    __tablename__ = "connector_configs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    connector_key = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    #: Secret fields inside are encrypted at rest by app.core.secrets.
    config = Column(JSON, nullable=False, default=dict)

    enabled = Column(Boolean, nullable=False, default=True)
    schedule_minutes = Column(Integer, nullable=True)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(20), nullable=True)
    last_run_summary = Column(JSON, nullable=True)

    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConnectorRun(Base):
    """History of one collection attempt — the audit trail for ingested data."""

    __tablename__ = "connector_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    connector_config_id = Column(
        Uuid, ForeignKey("connector_configs.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    connector_key = Column(String(100), nullable=False)

    #: queued | running | success | partial | failed
    status = Column(String(20), nullable=False, default="queued")
    trigger = Column(String(20), nullable=False, default="manual")

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    assets_found = Column(Integer, default=0)
    interfaces_found = Column(Integer, default=0)
    links_found = Column(Integer, default=0)
    vulnerabilities_found = Column(Integer, default=0)
    events_found = Column(Integer, default=0)

    written = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    triggered_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class IngestApiKey(Base):
    """Credential an endpoint agent presents when reporting in.

    Only the SHA-256 hash is stored; the plaintext key is shown once, at
    creation, and cannot be recovered afterwards.
    """

    __tablename__ = "ingest_api_keys"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(16), nullable=False)

    enabled = Column(Boolean, nullable=False, default=True)
    scope = Column(String(50), nullable=False, default="agent")

    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(64), nullable=True)
    use_count = Column(Integer, nullable=False, default=0)

    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
