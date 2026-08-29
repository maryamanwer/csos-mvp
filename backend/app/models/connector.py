"""SQL state for source definitions, executions and push credentials."""
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func

from app.core.database import Base


class ConnectorConfig(Base):
    __tablename__ = "connector_configs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    connector_key = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    schedule_minutes = Column(Integer)
    last_run_at = Column(DateTime(timezone=True))
    last_run_status = Column(String(20))
    last_run_summary = Column(JSON)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConnectorRun(Base):
    __tablename__ = "connector_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    connector_config_id = Column(Uuid, ForeignKey("connector_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_key = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    trigger = Column(String(20), nullable=False, default="manual")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    assets_found = Column(Integer, default=0)
    interfaces_found = Column(Integer, default=0)
    links_found = Column(Integer, default=0)
    vulnerabilities_found = Column(Integer, default=0)
    events_found = Column(Integer, default=0)
    written = Column(JSON)
    errors = Column(JSON)
    triggered_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))


class IngestApiKey(Base):
    __tablename__ = "ingest_api_keys"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(16), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    scope = Column(String(50), nullable=False, default="agent")
    last_used_at = Column(DateTime(timezone=True))
    last_used_ip = Column(String(64))
    use_count = Column(Integer, nullable=False, default=0)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
