"""CSOS discovery records shared by every source adapter.

Adapters are isolated from Neo4j and SQLAlchemy. They emit plain records and
the correlation pipeline decides how source evidence becomes graph state.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Literal

AssetType = Literal[
    "server", "application", "network_device", "router", "switch", "firewall",
    "endpoint", "workstation", "database", "cloud_resource", "identity", "other",
]
Criticality = Literal["low", "medium", "high", "critical"]
LinkType = Literal["CONNECTS_TO", "DEPENDS_ON", "HOSTS", "COMMUNICATES_WITH", "ROUTES_TO"]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class _GraphRecord:
    _excluded: frozenset[str] = frozenset()

    def graph_properties(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for item in fields(self):
            if item.name in self._excluded:
                continue
            value = getattr(self, item.name)
            if value not in (None, "", [], {}):
                values[item.name] = value
        return values


@dataclass
class CollectedAsset(_GraphRecord):
    source_ref: str
    name: str
    type: AssetType = "server"
    criticality: Criticality = "medium"
    environment: str = "production"
    owner: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    description: str | None = None
    vendor: str | None = None
    model: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None
    location: str | None = None
    edr_status: str | None = None
    edr_product: str | None = None
    edr_agent_version: str | None = None
    managed_status: str | None = None
    data_sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    _excluded = frozenset({"source_ref", "raw"})

    def graph_properties(self) -> dict[str, Any]:
        values = super().graph_properties()
        values["hostname"] = self.hostname or self.name
        if self.os_name or self.os_version:
            values["operating_system"] = " ".join(
                part for part in (self.os_name, self.os_version) if part
            )
        return values


@dataclass
class CollectedInterface(_GraphRecord):
    asset_ref: str
    name: str
    ip_address: str | None = None
    subnet_cidr: str | None = None
    mac_address: str | None = None
    status: str | None = None
    speed: str | None = None
    description: str | None = None
    vlan_id: str | None = None

    _excluded = frozenset({"asset_ref"})

    @property
    def key(self) -> str:
        return f"{self.asset_ref}::{self.name}"

    def graph_properties(self) -> dict[str, Any]:
        return {"key": self.key, **super().graph_properties()}


@dataclass
class CollectedLink(_GraphRecord):
    source_ref: str
    target_ref: str
    link_type: LinkType = "CONNECTS_TO"
    source_interface: str | None = None
    target_interface: str | None = None
    discovery_protocol: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    _excluded = frozenset({"source_ref", "target_ref", "link_type", "properties"})

    def graph_properties(self) -> dict[str, Any]:
        return {**super().graph_properties(), **self.properties}


@dataclass
class CollectedVulnerability:
    title: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    cvss_score: float = 0.0
    cve_id: str | None = None
    status: Literal[
        "open", "in_progress", "resolved", "accepted_risk", "mitigated",
        "accepted", "false_positive",
    ] = "open"
    description: str | None = None
    asset_refs: list[str] = field(default_factory=list)
    port: int | None = None
    service: str | None = None
    first_detected: str | None = None
    last_seen: str | None = None
    sla_due_at: str | None = None
    recommended_remediation: str | None = None
    data_sources: list[str] = field(default_factory=list)
    vendor_finding_id: str | None = None


@dataclass
class CollectedEvent:
    message: str
    source_ref: str | None = None
    source_ip: str | None = None
    severity: str | None = None
    facility: str | None = None
    hostname: str | None = None
    app_name: str | None = None
    timestamp: str = field(default_factory=utc_timestamp)
    raw: str | None = None


@dataclass
class CollectionResult:
    connector_key: str = ""
    assets: list[CollectedAsset] = field(default_factory=list)
    interfaces: list[CollectedInterface] = field(default_factory=list)
    links: list[CollectedLink] = field(default_factory=list)
    vulnerabilities: list[CollectedVulnerability] = field(default_factory=list)
    events: list[CollectedEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_timestamp)
    finished_at: str | None = None

    def merge(self, other: "CollectionResult") -> None:
        for name in ("assets", "interfaces", "links", "vulnerabilities", "events", "errors"):
            getattr(self, name).extend(getattr(other, name))

    def summary(self) -> dict[str, int]:
        return {
            name: len(getattr(self, name))
            for name in ("assets", "interfaces", "links", "vulnerabilities", "events", "errors")
        }
