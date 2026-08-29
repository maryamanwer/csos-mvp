"""Import authorized Nmap XML as CSOS asset and exposure evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from defusedxml import ElementTree

from app.connectors.base import BaseConnector, ConfigField, ConfigurationError, register_connector
from app.connectors.models import CollectedAsset, CollectedVulnerability, CollectionResult
from app.core.config import settings

_PORT_RULES = {
    21: ("FTP", "high", 8.1),
    23: ("Telnet", "critical", 9.8),
    3306: ("MySQL", "high", 8.2),
    5432: ("PostgreSQL", "high", 8.2),
    6379: ("Redis", "critical", 9.1),
    27017: ("MongoDB", "critical", 9.1),
}


def _short_name(value: str) -> str:
    return value.strip().split(".", 1)[0].upper()


def classify_from_os(os_name: str | None, services: list[str]) -> str:
    os_text = (os_name or "").lower()
    service_set = {service.lower() for service in services}
    if any(token in os_text for token in ("ios", "junos", "router", "switch")):
        return "network_device"
    if os_text:
        return "server"
    if service_set & {"mysql", "postgresql", "mongodb", "redis"}:
        return "database"
    return "server"


def parse_nmap_xml(xml_content: str | bytes) -> CollectionResult:
    result = CollectionResult(connector_key="nmap")
    try:
        root = ElementTree.fromstring(xml_content)
    except (ElementTree.ParseError, TypeError, ValueError) as error:
        result.errors.append(f"Invalid Nmap XML: {error}")
        return result

    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.get("state") != "up":
            continue
        addresses = {entry.get("addrtype"): entry for entry in host.findall("address")}
        ipv4 = addresses.get("ipv4")
        mac = addresses.get("mac")
        ip_address = ipv4.get("addr") if ipv4 is not None else None
        hostname_node = host.find("./hostnames/hostname")
        hostname = hostname_node.get("name") if hostname_node is not None else ip_address
        if not hostname:
            continue
        open_ports: list[tuple[int, str, str]] = []
        for port_node in host.findall("./ports/port"):
            state = port_node.find("state")
            if state is None or state.get("state") != "open":
                continue
            service = port_node.find("service")
            service_name = service.get("name", "unknown") if service is not None else "unknown"
            banner = " ".join(
                part for part in (
                    service.get("product") if service is not None else None,
                    service.get("version") if service is not None else None,
                ) if part
            )
            open_ports.append((int(port_node.get("portid", "0")), service_name, banner))

        os_node = host.find("./os/osmatch")
        os_name = os_node.get("name") if os_node is not None else None
        ref = _short_name(hostname)
        result.assets.append(CollectedAsset(
            source_ref=ref,
            name=hostname,
            hostname=hostname,
            ip_address=ip_address,
            mac_address=mac.get("addr") if mac is not None else None,
            vendor=mac.get("vendor") if mac is not None else None,
            os_name=os_name,
            type=classify_from_os(os_name, [item[1] for item in open_ports]),
            data_sources=["Nmap"],
            tags=["network-discovery"],
        ))
        for port, service_name, banner in open_ports:
            rule = _PORT_RULES.get(port)
            if rule is None:
                continue
            label, severity, score = rule
            result.vulnerabilities.append(CollectedVulnerability(
                title=f"{label} exposed on port {port}",
                severity=severity,
                cvss_score=score,
                description=f"Network scan detected service: {banner or service_name}",
                asset_refs=[ref],
                port=port,
                service=service_name,
                recommended_remediation="Limit the service to approved source networks and harden authentication.",
                data_sources=["Nmap"],
            ))
    return result


@register_connector
class NmapConnector(BaseConnector):
    key = "nmap"
    display_name = "Nmap XML import"
    description = "Imports approved Nmap XML results without initiating a scan."
    category = "scanner"
    config_fields = (
        ConfigField("xml_path", "XML file path", required=False),
        ConfigField("xml_content", "XML content", type="textarea", required=False),
    )

    def validate_config(self, config: dict[str, Any]) -> None:
        if not config.get("xml_path") and not config.get("xml_content"):
            raise ConfigurationError("Provide an XML file path or XML content")
        content = config.get("xml_content")
        if content and len(str(content).encode()) > settings.CONNECTOR_MAX_IMPORT_BYTES:
            raise ConfigurationError("Nmap XML content exceeds the import limit")

    @staticmethod
    def _safe_import_path(value: str) -> Path:
        root = Path(settings.CONNECTOR_IMPORT_ROOT).resolve()
        candidate = Path(value)
        candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if candidate != root and root not in candidate.parents:
            raise ConfigurationError(f"Import files must be inside {root}")
        return candidate

    # Kept as a public compatibility hook for callers that validate an import
    # location before starting a run.
    _import_path = _safe_import_path

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        self.validate_config(config)
        if config.get("xml_content"):
            return parse_nmap_xml(config["xml_content"])
        path = self._safe_import_path(str(config["xml_path"]))
        result = CollectionResult(connector_key=self.key)
        try:
            if path.stat().st_size > settings.CONNECTOR_MAX_IMPORT_BYTES:
                raise ConfigurationError("Nmap XML file exceeds the import limit")
            return parse_nmap_xml(path.read_bytes())
        except (OSError, ConfigurationError) as error:
            result.errors.append(f"Unable to import {path}: {error}")
            return result
