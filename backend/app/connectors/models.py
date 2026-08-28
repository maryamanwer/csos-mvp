"""Canonical collection model.

Every connector — SSH, SNMP, syslog, agent, nmap, file import — normalizes
whatever it finds into these structures. Nothing downstream of a connector
knows or cares which source produced the data, which is what makes the
collection layer extensible without touching the core.

``source_ref`` is the connector's own stable identifier for an entity
(hostname, chassis id, MAC, agent id). The graph writer uses it to correlate
the same real-world device seen by several connectors into one node.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

AssetType = Literal[
    "server",
    "application",
    "network_device",
    "router",
    "switch",
    "firewall",
    "endpoint",
    "workstation",
    "database",
    "cloud_resource",
    "identity",
    "other",
]

Criticality = Literal["low", "medium", "high", "critical"]

LinkType = Literal[
    "CONNECTS_TO",
    "DEPENDS_ON",
    "HOSTS",
    "COMMUNICATES_WITH",
    "ROUTES_TO",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CollectedAsset:
    """A device, host, or service discovered by a connector."""

    source_ref: str
    name: str
    type: AssetType = "server"
    criticality: Criticality = "medium"
    environment: str = "production"
    owner: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    description: str | None = None

    # Enrichment — optional, but this is what turns an inventory row into
    # something an architect or a vulnerability matcher can actually use.
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

    def graph_properties(self) -> dict[str, Any]:
        props = {
            "name": self.name,
            "type": self.type,
            "criticality": self.criticality,
            "environment": self.environment,
            "owner": self.owner,
            "hostname": self.hostname or self.name,
            "ip_address": self.ip_address,
            "description": self.description,
            "vendor": self.vendor,
            "model": self.model,
            "os_name": self.os_name,
            "operating_system": " ".join(
                part for part in (self.os_name, self.os_version) if part
            ) or None,
            "os_version": self.os_version,
            "serial_number": self.serial_number,
            "mac_address": self.mac_address,
            "location": self.location,
            "edr_status": self.edr_status,
            "edr_product": self.edr_product,
            "edr_agent_version": self.edr_agent_version,
            "managed_status": self.managed_status,
            "data_sources": self.data_sources,
            "tags": self.tags,
        }
        return {k: v for k, v in props.items() if v not in (None, "", [])}


@dataclass
class CollectedInterface:
    """A network interface belonging to a collected asset.

    Interfaces are what the original data model was missing entirely, and
    without them a real network topology cannot be represented at all.
    """

    asset_ref: str
    name: str
    ip_address: str | None = None
    subnet_cidr: str | None = None
    mac_address: str | None = None
    status: str | None = None
    speed: str | None = None
    description: str | None = None
    vlan_id: str | None = None

    @property
    def key(self) -> str:
        return f"{self.asset_ref}::{self.name}"

    def graph_properties(self) -> dict[str, Any]:
        props = {
            "key": self.key,
            "name": self.name,
            "ip_address": self.ip_address,
            "subnet_cidr": self.subnet_cidr,
            "mac_address": self.mac_address,
            "status": self.status,
            "speed": self.speed,
            "description": self.description,
            "vlan_id": self.vlan_id,
        }
        return {k: v for k, v in props.items() if v not in (None, "")}


@dataclass
class CollectedLink:
    """A discovered adjacency between two assets."""

    source_ref: str
    target_ref: str
    link_type: LinkType = "CONNECTS_TO"
    source_interface: str | None = None
    target_interface: str | None = None
    discovery_protocol: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def graph_properties(self) -> dict[str, Any]:
        props = {
            "source_interface": self.source_interface,
            "target_interface": self.target_interface,
            "discovery_protocol": self.discovery_protocol,
            **self.properties,
        }
        return {k: v for k, v in props.items() if v not in (None, "")}


@dataclass
class CollectedVulnerability:
    """A finding reported against one or more assets."""

    title: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    cvss_score: float = 0.0
    cve_id: str | None = None
    status: Literal[
        "open", "in_progress", "resolved", "accepted_risk",
        "mitigated", "accepted", "false_positive",
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
    """A log or telemetry event (syslog, agent heartbeat, audit trail)."""

    message: str
    source_ref: str | None = None
    source_ip: str | None = None
    severity: str | None = None
    facility: str | None = None
    hostname: str | None = None
    app_name: str | None = None
    timestamp: str = field(default_factory=_now)
    raw: str | None = None


@dataclass
class CollectionResult:
    """What a single connector run produced."""

    connector_key: str = ""
    assets: list[CollectedAsset] = field(default_factory=list)
    interfaces: list[CollectedInterface] = field(default_factory=list)
    links: list[CollectedLink] = field(default_factory=list)
    vulnerabilities: list[CollectedVulnerability] = field(default_factory=list)
    events: list[CollectedEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None

    def merge(self, other: "CollectionResult") -> None:
        self.assets.extend(other.assets)
        self.interfaces.extend(other.interfaces)
        self.links.extend(other.links)
        self.vulnerabilities.extend(other.vulnerabilities)
        self.events.extend(other.events)
        self.errors.extend(other.errors)

    def summary(self) -> dict[str, int]:
        return {
            "assets": len(self.assets),
            "interfaces": len(self.interfaces),
            "links": len(self.links),
            "vulnerabilities": len(self.vulnerabilities),
            "events": len(self.events),
            "errors": len(self.errors),
        }
