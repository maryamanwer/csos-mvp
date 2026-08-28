"""Nmap XML ingestion.

Rather than shelling out to nmap — which would put a scanning tool inside the
platform's trust boundary and inside its container — this connector consumes
the XML that nmap already produces. Scanning stays where it belongs, under the
operator's own authorization, and CSOS consumes the evidence.

    nmap -sV -O -oX estate.xml 10.0.0.0/24

The same XML is produced by masscan's nmap-compatible output and by most
scanner wrappers, so this covers more ground than the name suggests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from defusedxml import ElementTree as ET
except ModuleNotFoundError:  # development venvs created before Phase 3
    import xml.etree.ElementTree as ET

from app.connectors.base import (
    BaseConnector,
    ConfigField,
    ConfigurationError,
    register_connector,
)
from app.connectors.models import (
    CollectedAsset,
    CollectedInterface,
    CollectedVulnerability,
    CollectionResult,
)
from app.connectors.agent_ingest import NOTEWORTHY_PORTS
from app.connectors.ssh_network import normalize_device_id
from app.core.config import settings

OS_TO_ASSET_TYPE = (
    ("router", "network_device"),
    ("switch", "network_device"),
    ("firewall", "network_device"),
    ("ios", "network_device"),
    ("junos", "network_device"),
    ("windows", "server"),
    ("linux", "server"),
    ("bsd", "server"),
)


def classify_from_os(os_name: str | None, services: list[str]) -> str:
    text = (os_name or "").lower()
    for marker, asset_type in OS_TO_ASSET_TYPE:
        if marker in text:
            return asset_type
    if any(service in {"mysql", "postgresql", "ms-sql-s", "mongodb"} for service in services):
        return "database"
    if any(service in {"http", "https", "http-proxy"} for service in services):
        return "application"
    return "server"


def parse_nmap_xml(xml_content: str | bytes) -> CollectionResult:
    """Parse nmap XML into assets, interfaces and exposure findings."""
    result = CollectionResult(connector_key="nmap")

    raw = xml_content.decode("utf-8", errors="replace") if isinstance(xml_content, bytes) else xml_content
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        result.errors.append("Nmap XML declarations and entities are not permitted")
        return result
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        result.errors.append(f"Invalid XML: {exc}")
        return result

    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.get("state") != "up":
            continue

        ipv4 = None
        mac = None
        vendor = None
        for address in host.findall("address"):
            kind = address.get("addrtype")
            if kind == "ipv4":
                ipv4 = address.get("addr")
            elif kind == "mac":
                mac = address.get("addr")
                vendor = address.get("vendor")

        hostname = None
        hostnames = host.find("hostnames")
        if hostnames is not None:
            name_element = hostnames.find("hostname")
            if name_element is not None:
                hostname = name_element.get("name")

        if not ipv4 and not hostname:
            continue

        asset_ref = normalize_device_id(hostname) or (ipv4 or "")
        if not asset_ref:
            continue

        os_name = None
        os_element = host.find("os")
        if os_element is not None:
            match = os_element.find("osmatch")
            if match is not None:
                os_name = match.get("name")

        services: list[str] = []
        open_ports: list[tuple[int, str, str | None, str | None]] = []
        ports_element = host.find("ports")
        if ports_element is not None:
            for port in ports_element.findall("port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                try:
                    port_number = int(port.get("portid", ""))
                except ValueError:
                    continue
                service_element = port.find("service")
                service_name = (
                    service_element.get("name") if service_element is not None else None
                ) or "unknown"
                product = (
                    service_element.get("product") if service_element is not None else None
                )
                version = (
                    service_element.get("version") if service_element is not None else None
                )
                services.append(service_name)
                open_ports.append((port_number, service_name, product, version))

        result.assets.append(
            CollectedAsset(
                source_ref=asset_ref,
                name=hostname or ipv4 or asset_ref,
                type=classify_from_os(os_name, services),  # type: ignore[arg-type]
                criticality="medium",
                ip_address=ipv4,
                mac_address=mac,
                vendor=vendor,
                os_name=os_name,
                description="Discovered by an authorized Nmap scan",
                tags=["nmap", "discovered"],
                raw={"open_ports": [port for port, *_ in open_ports]},
            )
        )

        if ipv4:
            result.interfaces.append(
                CollectedInterface(
                    asset_ref=asset_ref,
                    name="nic0",
                    ip_address=ipv4,
                    mac_address=mac,
                    status="up",
                )
            )

        for port_number, service_name, product, version in open_ports:
            if port_number not in NOTEWORTHY_PORTS:
                continue
            label, severity, score, explanation = NOTEWORTHY_PORTS[port_number]
            banner = " ".join(part for part in (product, version) if part)
            result.vulnerabilities.append(
                CollectedVulnerability(
                    title=f"{label} exposed on port {port_number}",
                    severity=severity,  # type: ignore[arg-type]
                    cvss_score=score,
                    description=f"{explanation}. Detected service: {banner or service_name}",
                    asset_refs=[asset_ref],
                    port=port_number,
                    service=service_name,
                )
            )

    return result


@register_connector
class NmapConnector(BaseConnector):
    key = "nmap"
    display_name = "Nmap XML Results"
    description = (
        "Imports authorized Nmap XML output as assets, interfaces and exposed services."
    )
    category = "scanner"

    config_fields = (
        ConfigField(
            "xml_path",
            "XML file path",
            help="A file path mounted inside the collection worker container",
            required=False,
        ),
        ConfigField(
            "xml_content", "XML content", type="textarea", required=False
        ),
    )

    def validate_config(self, config: dict[str, Any]) -> None:
        if not config.get("xml_path") and not config.get("xml_content"):
            raise ConfigurationError("Provide an XML file path or paste XML content")
        content = config.get("xml_content")
        if content and len(str(content).encode("utf-8")) > settings.CONNECTOR_MAX_IMPORT_BYTES:
            raise ConfigurationError("Nmap XML content exceeds CONNECTOR_MAX_IMPORT_BYTES")

    @staticmethod
    def _import_path(value: str) -> Path:
        root = Path(settings.CONNECTOR_IMPORT_ROOT).resolve()
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if candidate != root and root not in candidate.parents:
            raise ConfigurationError(
                f"Nmap XML files must be inside {settings.CONNECTOR_IMPORT_ROOT}"
            )
        return candidate

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        config = self.apply_defaults(config)
        self.validate_config(config)

        content = config.get("xml_content")
        if not content:
            path = self._import_path(str(config["xml_path"]))
            try:
                if path.stat().st_size > settings.CONNECTOR_MAX_IMPORT_BYTES:
                    raise ConfigurationError(
                        "Nmap XML file exceeds CONNECTOR_MAX_IMPORT_BYTES"
                    )
                with open(path, "rb") as handle:
                    content = handle.read()
            except (OSError, ConfigurationError) as exc:
                result = CollectionResult(connector_key=self.key)
                result.errors.append(f"Unable to read {path}: {exc}")
                return result

        return parse_nmap_xml(content)
