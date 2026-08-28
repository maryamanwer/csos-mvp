"""Endpoint agent ingestion.

The agent (``agent/csos_agent.py``) runs on a server or workstation, gathers
local inventory using nothing but the Python standard library, and POSTs a JSON
document to ``/api/v1/ingest/agent``. This connector normalizes that document.

Keeping the normalizer here rather than in the API route means the agent format
is validated in one place and can be unit-tested without HTTP.
"""
from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector, ConfigField, register_connector
from app.connectors.models import (
    CollectedAsset,
    CollectedInterface,
    CollectedVulnerability,
    CollectionResult,
)
from app.connectors.ssh_network import normalize_device_id

#: Ports whose exposure is worth flagging on an endpoint. Deliberately short —
#: a long list produces noise that buries the findings that matter.
NOTEWORTHY_PORTS = {
    21: ("FTP", "high", 7.5, "Unencrypted file-transfer service"),
    23: ("Telnet", "critical", 9.0, "Unencrypted remote administration"),
    445: ("SMB", "high", 7.0, "File sharing exposed to lateral movement"),
    3389: ("RDP", "high", 7.5, "Remote desktop exposed to the network"),
    5900: ("VNC", "high", 7.0, "Remote control commonly deployed without strong authentication"),
    1433: ("MSSQL", "medium", 6.0, "Database service exposed to the network"),
    3306: ("MySQL", "medium", 6.0, "Database service exposed to the network"),
    27017: ("MongoDB", "high", 7.5, "Database service commonly left without authentication"),
    6379: ("Redis", "high", 7.5, "Data store commonly left without authentication"),
    9200: ("Elasticsearch", "high", 7.5, "Search index commonly left open"),
}


def normalize_agent_payload(payload: dict[str, Any]) -> CollectionResult:
    """Convert one agent report into canonical form.

    Tolerant by design: agents run on machines nobody is watching, so a missing
    or malformed section degrades that section only.
    """
    result = CollectionResult(connector_key="agent")

    hostname = str(payload.get("hostname") or "").strip()
    agent_id = str(payload.get("agent_id") or "").strip()
    asset_ref = normalize_device_id(hostname) or agent_id
    if not asset_ref:
        result.errors.append("Agent report has no hostname or agent identifier")
        return result

    system = payload.get("system") or {}
    network = payload.get("network") or {}

    primary_ip = None
    interfaces_payload = network.get("interfaces") or []
    for entry in interfaces_payload:
        address = entry.get("ip_address")
        if address and not str(address).startswith("127."):
            primary_ip = address
            break

    result.assets.append(
        CollectedAsset(
            source_ref=asset_ref,
            name=hostname or asset_ref,
            type=str(payload.get("asset_type") or "server"),  # type: ignore[arg-type]
            criticality=str(payload.get("criticality") or "medium"),  # type: ignore[arg-type]
            environment=str(payload.get("environment") or "production"),
            owner=payload.get("owner"),
            ip_address=primary_ip,
            os_name=system.get("os_name"),
            os_version=system.get("os_version"),
            vendor=system.get("vendor"),
            model=system.get("model"),
            serial_number=system.get("serial_number"),
            mac_address=network.get("primary_mac"),
            description=f"Reported by CSOS endpoint agent ({agent_id or 'unknown'})",
            tags=["agent"],
            raw={
                "agent_version": payload.get("agent_version"),
                "reported_at": payload.get("reported_at"),
                "package_count": len(payload.get("packages") or []),
            },
        )
    )

    for entry in interfaces_payload:
        name = entry.get("name")
        if not name:
            continue
        result.interfaces.append(
            CollectedInterface(
                asset_ref=asset_ref,
                name=str(name),
                ip_address=entry.get("ip_address"),
                subnet_cidr=entry.get("subnet_cidr"),
                mac_address=entry.get("mac_address"),
                status=entry.get("status"),
            )
        )

    for entry in payload.get("listening_ports") or []:
        try:
            port = int(entry.get("port"))
        except (TypeError, ValueError):
            continue
        if port not in NOTEWORTHY_PORTS:
            continue
        service, severity, score, explanation = NOTEWORTHY_PORTS[port]
        listen_address = str(entry.get("address") or "")
        # A service bound to loopback is not network-exposed.
        if listen_address.startswith("127.") or listen_address == "::1":
            continue
        result.vulnerabilities.append(
            CollectedVulnerability(
                title=f"{service} exposed on port {port}",
                severity=severity,  # type: ignore[arg-type]
                cvss_score=score,
                description=explanation,
                asset_refs=[asset_ref],
                port=port,
                service=service,
            )
        )

    return result


@register_connector
class AgentConnector(BaseConnector):
    key = "agent"
    display_name = "CSOS Endpoint Agent"
    description = (
        "Receives inventory reports from CSOS agents installed on servers and endpoints."
    )
    category = "endpoint"
    schedulable = False

    config_fields = (
        ConfigField("enabled", "Enabled", type="boolean", default=True, required=False),
        ConfigField(
            "require_api_key",
            "Require API key",
            type="boolean",
            default=True,
            required=False,
        ),
    )

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        result = CollectionResult(connector_key=self.key)
        result.errors.append(
            "The agent is push-based and reports to /api/v1/ingest/agent"
        )
        return result

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        return True, "Agent ingestion endpoint is ready at /api/v1/ingest/agent"
