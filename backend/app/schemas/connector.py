"""Request and response models for the collection API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectorFieldOut(BaseModel):
    name: str
    label: str
    type: str = "string"
    required: bool = True
    secret: bool = False
    default: Any = None
    help: str | None = None
    choices: list[str] | None = None


class ConnectorTypeOut(BaseModel):
    """A connector the platform knows how to run."""

    key: str
    display_name: str
    description: str
    category: str
    schedulable: bool
    config_fields: list[ConnectorFieldOut] = Field(default_factory=list)


class ConnectorConfigCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    connector_key: str = Field(min_length=1, max_length=100)
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    schedule_minutes: int | None = Field(default=None, ge=5, le=10080)


class ConnectorConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    schedule_minutes: int | None = Field(default=None, ge=5, le=10080)


class ConnectorConfigOut(BaseModel):
    """Configuration as returned to a client — secrets are always redacted."""

    id: uuid.UUID
    name: str
    connector_key: str
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool
    schedule_minutes: int | None = None
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    last_run_summary: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConnectorRunOut(BaseModel):
    id: uuid.UUID
    connector_config_id: uuid.UUID
    connector_key: str
    status: str
    trigger: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    assets_found: int = 0
    interfaces_found: int = 0
    links_found: int = 0
    vulnerabilities_found: int = 0
    events_found: int = 0
    written: dict[str, Any] | None = None
    errors: list[str] | None = None

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    success: bool
    message: str


# --- agent ingestion ---------------------------------------------------

class AgentInterface(BaseModel):
    name: str
    ip_address: str | None = None
    subnet_cidr: str | None = None
    mac_address: str | None = None
    status: str | None = None


class AgentListeningPort(BaseModel):
    port: int
    address: str | None = None
    protocol: str | None = "tcp"
    process: str | None = None


class AgentSystem(BaseModel):
    os_name: str | None = None
    os_version: str | None = None
    vendor: str | None = None
    model: str | None = None
    serial_number: str | None = None


class AgentNetwork(BaseModel):
    primary_mac: str | None = None
    interfaces: list[AgentInterface] = Field(default_factory=list)


class AgentReport(BaseModel):
    """What an endpoint agent posts to /api/v1/ingest/agent."""

    agent_id: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)
    agent_version: str | None = None
    reported_at: str | None = None
    asset_type: Literal[
        "server", "application", "network_device", "endpoint", "workstation",
        "database", "cloud_resource"
    ] = "server"
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    environment: str = "production"
    owner: str | None = None
    system: AgentSystem = Field(default_factory=AgentSystem)
    network: AgentNetwork = Field(default_factory=AgentNetwork)
    listening_ports: list[AgentListeningPort] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)


class SyslogBatch(BaseModel):
    """Log lines forwarded over HTTP, for networks that cannot reach port 514."""

    lines: list[str] = Field(min_length=1, max_length=5000)
    source_ip: str | None = None


class IngestResult(BaseModel):
    accepted: bool
    written: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


# --- API keys ----------------------------------------------------------

class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    scope: Literal["agent", "syslog"] = "agent"
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scope: str
    enabled: bool
    last_used_at: datetime | None = None
    use_count: int = 0
    created_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    """Returned once at creation — the only time the plaintext key exists."""

    api_key: str
