"""CSOS network CLI adapter.

The parser intentionally produces evidence rather than device-specific objects:
inventory, interfaces and neighbour relationships all enter the same pipeline.
"""
from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

from app.connectors.base import BaseConnector, ConfigField, ConfigurationError, register_connector
from app.connectors.models import CollectedAsset, CollectedInterface, CollectedLink, CollectionResult
from app.core.network_policy import TargetPolicyError, validate_connector_target

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ["cisco_ios", "cisco_nxos", "juniper_junos", "arista_eos", "fortinet"]
COMMANDS = {
    "cisco_ios": {"version": "show version", "interfaces": "show ip interface brief", "cdp": "show cdp neighbors detail", "lldp": "show lldp neighbors detail"},
    "cisco_nxos": {"version": "show version", "interfaces": "show ip interface brief", "cdp": "show cdp neighbors detail", "lldp": "show lldp neighbors detail"},
    "juniper_junos": {"version": "show version", "interfaces": "show interfaces terse", "lldp": "show lldp neighbors detail"},
    "arista_eos": {"version": "show version", "interfaces": "show ip interface brief", "lldp": "show lldp neighbors detail"},
    "fortinet": {"version": "get system status", "interfaces": "get system interface", "lldp": "diagnose lldprx neighbor summary"},
}
VENDOR_BY_PLATFORM = {
    "cisco_ios": "Cisco", "cisco_nxos": "Cisco", "juniper_junos": "Juniper",
    "arista_eos": "Arista", "fortinet": "Fortinet",
}


def normalize_device_id(device_id: str | None) -> str:
    if not device_id:
        return ""
    value = device_id.strip().split(".", 1)[0]
    value = re.sub(r"\([^)]*\)$", "", value)
    return value.strip().upper()


def derive_cidr(ip_address: str | None, prefix: str | None) -> str | None:
    if not ip_address or not prefix:
        return None
    try:
        return str(ipaddress.ip_network(f"{ip_address}/{prefix}", strict=False))
    except ValueError:
        return None


def _version_facts(platform: str, text: str, fallback: str) -> dict[str, str | None]:
    hostname = fallback
    uptime = re.search(r"(?m)^([\w.-]+)\s+uptime is", text)
    if uptime:
        hostname = uptime.group(1)
    version = re.search(r"\bVersion\s+([^,\s]+)", text, re.IGNORECASE)
    model_patterns = [
        r"(?m)^Cisco\s+([^\s]+)\s+\([^\n]+\)\s+processor",
        r"(?im)^Model(?: number)?:\s*(\S+)",
        r"(?im)^Hardware:\s*(\S+)",
    ]
    model = next((match.group(1) for pattern in model_patterns if (match := re.search(pattern, text))), None)
    serial = None
    for pattern in (r"Processor board ID\s+(\S+)", r"(?im)^Serial(?: Number)?:\s*(\S+)"):
        match = re.search(pattern, text)
        if match:
            serial = match.group(1)
            break
    os_name = {
        "cisco_ios": "Cisco IOS", "cisco_nxos": "Cisco NX-OS", "juniper_junos": "Junos",
        "arista_eos": "Arista EOS", "fortinet": "FortiOS",
    }.get(platform)
    return {"hostname": hostname, "os_version": version.group(1) if version else None, "model": model, "serial_number": serial, "os_name": os_name}


def _interfaces(text: str, asset_ref: str) -> list[CollectedInterface]:
    found: list[CollectedInterface] = []
    for line in text.splitlines():
        columns = line.split()
        if len(columns) < 3 or columns[0].lower().startswith("interface"):
            continue
        name, address = columns[0], columns[1]
        if not re.match(r"^[A-Za-z][A-Za-z0-9./:_-]+$", name):
            continue
        if address.lower() == "unassigned":
            ip_value = None
        else:
            try:
                ipaddress.ip_address(address)
                ip_value = address
            except ValueError:
                continue
        status_text = " ".join(columns[4:-1]).lower() if len(columns) > 5 else columns[-2].lower()
        protocol = columns[-1].lower()
        found.append(CollectedInterface(
            asset_ref=asset_ref, name=name, ip_address=ip_value,
            status="up" if status_text == "up" and protocol == "up" else "down",
        ))
    return found


def _neighbor_blocks(text: str) -> list[str]:
    return [block for block in re.split(r"^-{5,}\s*$", text, flags=re.MULTILINE) if "Device ID:" in block or "System Name:" in block]


def _neighbors(text: str, local_ref: str, protocol: str) -> tuple[list[CollectedAsset], list[CollectedLink]]:
    assets: list[CollectedAsset] = []
    links: list[CollectedLink] = []
    seen: set[str] = set()
    for block in _neighbor_blocks(text):
        id_match = re.search(r"(?:Device ID|System Name):\s*(\S+)", block, re.IGNORECASE)
        if not id_match:
            continue
        remote_ref = normalize_device_id(id_match.group(1))
        if not remote_ref or remote_ref == local_ref:
            continue
        local_port = re.search(r"Interface:\s*([^,\n]+)", block, re.IGNORECASE)
        remote_port = re.search(r"(?:Port ID \(outgoing port\)|Port id):\s*([^\n]+)", block, re.IGNORECASE)
        remote_ip = re.search(r"IP address:\s*([^\s]+)", block, re.IGNORECASE)
        platform = re.search(r"Platform:\s*([^,\n]+)", block, re.IGNORECASE)
        if remote_ref not in seen:
            assets.append(CollectedAsset(
                source_ref=remote_ref, name=remote_ref, type="network_device",
                ip_address=remote_ip.group(1) if remote_ip else None,
                model=platform.group(1).strip() if platform else None,
                description=f"Observed through {protocol.upper()} from {local_ref}",
                tags=["discovered", protocol.lower()],
            ))
            seen.add(remote_ref)
        links.append(CollectedLink(
            source_ref=local_ref, target_ref=remote_ref,
            source_interface=local_port.group(1).strip() if local_port else None,
            target_interface=remote_port.group(1).strip() if remote_port else None,
            discovery_protocol=protocol.upper(),
        ))
    return assets, links


def build_device_result(
    platform: str,
    host: str,
    outputs: dict[str, str],
    *,
    environment: str = "production",
    criticality: str = "high",
    owner: str | None = None,
) -> CollectionResult:
    result = CollectionResult(connector_key="ssh_network")
    facts = _version_facts(platform, outputs.get("version", ""), host)
    ref = normalize_device_id(str(facts["hostname"])) or normalize_device_id(host)
    result.assets.append(CollectedAsset(
        source_ref=ref, name=str(facts["hostname"]), hostname=str(facts["hostname"]),
        type="network_device", criticality=criticality, environment=environment,
        owner=owner, ip_address=host, vendor=VENDOR_BY_PLATFORM.get(platform),
        model=facts["model"], os_name=facts["os_name"], os_version=facts["os_version"],
        serial_number=facts["serial_number"], data_sources=["Network CLI"], tags=["ssh", platform],
    ))
    result.interfaces.extend(_interfaces(outputs.get("interfaces", ""), ref))
    for protocol in ("cdp", "lldp"):
        assets, links = _neighbors(outputs.get(protocol, ""), ref, protocol)
        result.assets.extend(assets)
        result.links.extend(links)
    return result


@register_connector
class SSHNetworkConnector(BaseConnector):
    key = "ssh_network"
    display_name = "Network CLI"
    description = "Collects approved network inventory, interfaces and neighbours over SSH."
    category = "network"
    config_fields = (
        ConfigField("hosts", "Device addresses", type="textarea"),
        ConfigField("device_type", "Device type", type="select", choices=SUPPORTED_PLATFORMS, default="cisco_ios"),
        ConfigField("username", "Username"),
        ConfigField("password", "Password", secret=True),
        ConfigField("enable_secret", "Enable secret", secret=True, required=False),
        ConfigField("port", "Port", type="number", required=False, default=22),
        ConfigField("verify_host_key", "Verify SSH host key", type="boolean", required=False, default=True),
        ConfigField("timeout", "Timeout (seconds)", type="number", required=False, default=30),
        ConfigField("environment", "Environment", required=False, default="production"),
        ConfigField("criticality", "Criticality", type="select", choices=["low", "medium", "high", "critical"], required=False, default="high"),
        ConfigField("owner", "Owner", required=False),
    )

    @staticmethod
    def _hosts(config: dict[str, Any]) -> list[str]:
        raw = config.get("hosts") or []
        values = raw if isinstance(raw, list) else str(raw).replace(",", "\n").splitlines()
        return [str(item).strip() for item in values if str(item).strip()]

    def validate_config(self, config: dict[str, Any]) -> None:
        super().validate_config(config)
        hosts = self._hosts(config)
        if not hosts:
            raise ConfigurationError("At least one device address is required")
        if config.get("device_type", "cisco_ios") not in SUPPORTED_PLATFORMS:
            raise ConfigurationError("Unsupported device type")
        for host in hosts:
            try:
                validate_connector_target(host)
            except TargetPolicyError as error:
                raise ConfigurationError(str(error)) from error

    def _collect_host(self, host: str, platform: str, config: dict[str, Any]) -> dict[str, str]:
        from netmiko import ConnectHandler
        parameters = {
            "device_type": platform, "host": host, "username": config["username"],
            "password": config["password"], "port": int(config.get("port", 22)),
            "conn_timeout": int(config.get("timeout", 30)), "fast_cli": False,
            "ssh_strict": bool(config.get("verify_host_key", True)),
            "system_host_keys": bool(config.get("verify_host_key", True)),
        }
        if config.get("enable_secret"):
            parameters["secret"] = config["enable_secret"]
        captured: dict[str, str] = {}
        with ConnectHandler(**parameters) as connection:
            if config.get("enable_secret"):
                connection.enable()
            for capability, command in COMMANDS.get(platform, {}).items():
                try:
                    captured[capability] = connection.send_command(command, read_timeout=int(config.get("timeout", 30)))
                except Exception as error:  # one unsupported command must not discard the device
                    logger.info("%s did not return %s: %s", host, capability, error)
                    captured[capability] = ""
        return captured

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        ready = self.apply_defaults(config)
        try:
            self.validate_config(ready)
            host = self._hosts(ready)[0]
            output = self._collect_host(host, ready["device_type"], ready)
            return True, f"Connected to {host}; received {sum(bool(value) for value in output.values())} command results"
        except Exception as error:
            return False, str(error)

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        ready = self.apply_defaults(config)
        self.validate_config(ready)
        aggregate = CollectionResult(connector_key=self.key)
        for host in self._hosts(ready):
            try:
                output = self._collect_host(host, ready["device_type"], ready)
                aggregate.merge(build_device_result(
                    ready["device_type"], host, output,
                    environment=ready.get("environment", "production"),
                    criticality=ready.get("criticality", "high"), owner=ready.get("owner"),
                ))
            except Exception as error:
                aggregate.errors.append(f"{host}: {error}")
        return aggregate
