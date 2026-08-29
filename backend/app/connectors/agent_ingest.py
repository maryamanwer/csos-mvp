"""Translate CSOS endpoint observations into the platform evidence model."""
from __future__ import annotations

import ipaddress
from typing import Any

from app.connectors.base import BaseConnector, ConfigField, register_connector
from app.connectors.models import (
    CollectedAsset, CollectedInterface, CollectedVulnerability, CollectionResult,
)

_EXPOSURE_RULES = {
    21: ("FTP", "high", 8.1, "Disable clear-text FTP or restrict it to an approved management network."),
    23: ("Telnet", "critical", 9.8, "Disable Telnet and use an authenticated encrypted management protocol."),
    3306: ("MySQL", "high", 8.2, "Restrict database access to approved application hosts."),
    5432: ("PostgreSQL", "high", 8.2, "Restrict database access to approved application hosts."),
    6379: ("Redis", "critical", 9.1, "Bind Redis to a private interface and require authentication."),
    27017: ("MongoDB", "critical", 9.1, "Restrict MongoDB exposure and enable authentication."),
}


def _identity(hostname: str) -> str:
    return hostname.strip().split(".", 1)[0].upper()


def _network_reachable(address: str | None) -> bool:
    if not address or address in {"*", "0.0.0.0", "::", "[::]"}:
        return True
    try:
        return not ipaddress.ip_address(address.strip("[]")).is_loopback
    except ValueError:
        return True


def _primary_address(interfaces: list[dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for interface in interfaces:
        value = interface.get("ip_address")
        if not value:
            continue
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not address.is_loopback and not address.is_link_local:
            candidates.append(value)
    return candidates[0] if candidates else None


def normalize_agent_payload(payload: dict[str, Any]) -> CollectionResult:
    result = CollectionResult(connector_key="agent")
    hostname = str(payload.get("hostname") or "").strip()
    agent_id = str(payload.get("agent_id") or "").strip()
    if not hostname and not agent_id:
        result.errors.append("Endpoint report does not contain a usable identity")
        return result

    source_ref = _identity(hostname) or agent_id.upper()
    system = payload.get("system") or {}
    network = payload.get("network") or {}
    raw_interfaces = network.get("interfaces") or []
    result.assets.append(CollectedAsset(
        source_ref=source_ref,
        name=hostname or agent_id,
        hostname=hostname or None,
        type=payload.get("asset_type") or "server",
        criticality=payload.get("criticality") or "medium",
        environment=payload.get("environment") or "production",
        owner=payload.get("owner"),
        ip_address=_primary_address(raw_interfaces),
        mac_address=network.get("primary_mac"),
        vendor=system.get("vendor"),
        model=system.get("model"),
        os_name=system.get("os_name"),
        os_version=system.get("os_version"),
        serial_number=system.get("serial_number"),
        managed_status="managed",
        data_sources=["CSOS Endpoint Agent"],
        tags=["endpoint-agent"],
    ))

    for item in raw_interfaces:
        if not item.get("name"):
            continue
        result.interfaces.append(CollectedInterface(
            asset_ref=source_ref,
            name=str(item["name"]),
            ip_address=item.get("ip_address"),
            subnet_cidr=item.get("subnet_cidr"),
            mac_address=item.get("mac_address"),
            status=item.get("status"),
        ))

    for listener in payload.get("listening_ports") or []:
        port = int(listener.get("port") or 0)
        rule = _EXPOSURE_RULES.get(port)
        if rule is None or not _network_reachable(listener.get("address")):
            continue
        service, severity, score, remediation = rule
        result.vulnerabilities.append(CollectedVulnerability(
            title=f"Exposed {service} service",
            severity=severity,
            cvss_score=score,
            description=f"{service} is listening on a network-reachable interface.",
            asset_refs=[source_ref],
            port=port,
            service=service.lower(),
            recommended_remediation=remediation,
            data_sources=["CSOS Endpoint Agent"],
        ))
    return result


@register_connector
class AgentConnector(BaseConnector):
    key = "agent"
    display_name = "CSOS Endpoint Agent"
    description = "Accepts authenticated endpoint inventory and exposure reports."
    category = "endpoint"
    schedulable = False
    config_fields = (
        ConfigField("enabled", "Enabled", type="boolean", required=False, default=True),
        ConfigField("require_api_key", "Require API key", type="boolean", required=False, default=True),
    )

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        result = CollectionResult(connector_key=self.key)
        result.errors.append("Endpoint reports arrive through /api/v1/ingest/agent")
        return result

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        return True, "Endpoint ingestion is available."
