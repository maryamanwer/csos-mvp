"""SSH connector for network devices.

Logs into routers, switches and firewalls, reads their operational state, and
turns it into assets, interfaces and adjacencies. This is the connector that
makes a real network diagram possible: neighbour discovery (CDP/LLDP) supplies
the links, and ``show ip interface brief`` supplies the addressing.

Parsing is delegated to ntc-templates (TextFSM) rather than hand-written
regular expressions, so adding a platform is a matter of naming its commands.
The ``_parse_*`` helpers take raw command output and are pure functions, which
keeps them testable without a live device.
"""
from __future__ import annotations

import ipaddress
import logging
from typing import Any

from app.connectors.base import (
    BaseConnector,
    ConfigField,
    ConfigurationError,
    register_connector,
)
from app.connectors.models import (
    CollectedAsset,
    CollectedInterface,
    CollectedLink,
    CollectionResult,
)
from app.core.network_policy import TargetPolicyError, validate_connector_target

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = [
    "cisco_ios",
    "cisco_xe",
    "cisco_nxos",
    "cisco_asa",
    "arista_eos",
    "juniper_junos",
    "hp_procurve",
    "fortinet",
    "paloalto_panos",
]

#: Command per platform per capability. A missing entry is skipped silently,
#: so a platform can support inventory without supporting neighbour discovery.
COMMANDS: dict[str, dict[str, str]] = {
    "cisco_ios": {
        "version": "show version",
        "interfaces": "show ip interface brief",
        "cdp": "show cdp neighbors detail",
        "lldp": "show lldp neighbors detail",
        "vlans": "show vlan brief",
    },
    "cisco_xe": {
        "version": "show version",
        "interfaces": "show ip interface brief",
        "cdp": "show cdp neighbors detail",
        "lldp": "show lldp neighbors detail",
        "vlans": "show vlan brief",
    },
    "cisco_nxos": {
        "version": "show version",
        "interfaces": "show ip interface brief",
        "cdp": "show cdp neighbors detail",
        "lldp": "show lldp neighbors detail",
        "vlans": "show vlan brief",
    },
    "cisco_asa": {
        "version": "show version",
        "interfaces": "show interface ip brief",
    },
    "arista_eos": {
        "version": "show version",
        "interfaces": "show ip interface brief",
        "lldp": "show lldp neighbors detail",
        "vlans": "show vlan",
    },
    "juniper_junos": {
        "version": "show version",
        "interfaces": "show interfaces terse",
        "lldp": "show lldp neighbors",
    },
    "hp_procurve": {
        "version": "show version",
        "interfaces": "show ip",
        "lldp": "show lldp info remote-device",
    },
    "fortinet": {
        "version": "get system status",
        "interfaces": "get system interface",
    },
    "paloalto_panos": {
        "version": "show system info",
        "interfaces": "show interface all",
    },
}

VENDOR_BY_PLATFORM = {
    "cisco_ios": "Cisco",
    "cisco_xe": "Cisco",
    "cisco_nxos": "Cisco",
    "cisco_asa": "Cisco",
    "arista_eos": "Arista",
    "juniper_junos": "Juniper",
    "hp_procurve": "HP",
    "fortinet": "Fortinet",
    "paloalto_panos": "Palo Alto Networks",
}


# --------------------------------------------------------------------------
# Pure parsing helpers — no device or network access, so they unit-test cleanly
# --------------------------------------------------------------------------

def normalize_device_id(device_id: str | None) -> str:
    """CDP and LLDP report FQDNs inconsistently; correlate on the short name.

    ``R2.corp.example.com(FDO1234)`` and ``R2`` must resolve to the same node,
    otherwise every neighbour becomes a duplicate device in the graph.
    """
    if not device_id:
        return ""
    name = str(device_id).strip()
    if "(" in name:
        name = name.split("(", 1)[0]
    name = name.split(".", 1)[0]
    return name.strip().upper()


def _textfsm_parse(platform: str, command: str, output: str) -> list[dict[str, Any]]:
    """Parse raw CLI output with ntc-templates; return [] when unsupported."""
    if not output or not output.strip():
        return []
    try:
        from ntc_templates.parse import parse_output

        parsed = parse_output(platform=platform, command=command, data=output)
        return parsed if isinstance(parsed, list) else []
    except Exception as exc:  # noqa: BLE001 - template gaps must not fail a run
        logger.debug("Unable to parse '%s' for %s: %s", command, platform, exc)
        return []


def _first(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        if value not in (None, "", "unassigned", "unset"):
            return str(value).strip()
    return None


def parse_version(platform: str, output: str, fallback_host: str) -> dict[str, Any]:
    """Extract hostname, OS version, model and serial from ``show version``."""
    command = COMMANDS.get(platform, {}).get("version", "show version")
    rows = _textfsm_parse(platform, command, output)
    row = rows[0] if rows else {}
    return {
        "hostname": _first(row, "hostname", "host_name", "device_name") or fallback_host,
        "os_version": _first(row, "version", "os_version", "software_version"),
        "model": _first(row, "hardware", "model", "platform", "pid"),
        "serial_number": _first(row, "serial", "serial_number", "chassis_id"),
        "os_name": _first(row, "software_image", "os") or platform,
    }


def parse_interfaces(
    platform: str, output: str, asset_ref: str
) -> list[CollectedInterface]:
    """Extract interfaces and their addressing."""
    command = COMMANDS.get(platform, {}).get("interfaces", "")
    interfaces: list[CollectedInterface] = []
    for row in _textfsm_parse(platform, command, output):
        name = _first(row, "interface", "intf", "port", "name")
        if not name:
            continue
        ip_address = _first(row, "ip_address", "ipaddr", "ip", "local_ip")
        prefix = _first(row, "prefix_length", "mask", "netmask")
        interfaces.append(
            CollectedInterface(
                asset_ref=asset_ref,
                name=name,
                ip_address=ip_address,
                subnet_cidr=derive_cidr(ip_address, prefix),
                status=_first(row, "status", "link_status", "admin_state"),
                description=_first(row, "description", "descr"),
                mac_address=_first(row, "mac_address", "mac", "address"),
                speed=_first(row, "speed", "bandwidth"),
            )
        )
    return interfaces


def derive_cidr(ip_address: str | None, prefix: str | None) -> str | None:
    """Turn an address plus mask or prefix length into a network CIDR."""
    if not ip_address:
        return None
    try:
        if prefix in (None, ""):
            return None
        prefix_str = str(prefix).strip()
        if "." in prefix_str:  # dotted-quad netmask
            network = ipaddress.ip_network(f"{ip_address}/{prefix_str}", strict=False)
        else:
            network = ipaddress.ip_network(
                f"{ip_address}/{int(prefix_str)}", strict=False
            )
        return str(network)
    except (ValueError, TypeError):
        return None


def parse_neighbors(
    platform: str, output: str, asset_ref: str, protocol: str
) -> tuple[list[CollectedAsset], list[CollectedLink]]:
    """Extract adjacencies from CDP or LLDP output.

    Returns lightly-populated placeholder assets for neighbours that have not
    been polled directly, so the topology stays connected even when only part
    of the estate is reachable.
    """
    command = COMMANDS.get(platform, {}).get(protocol, "")
    if not command:
        return [], []

    neighbours: list[CollectedAsset] = []
    links: list[CollectedLink] = []

    for row in _textfsm_parse(platform, command, output):
        remote_raw = _first(
            row, "destination_host", "neighbor", "neighbor_name", "device_id",
            "system_name", "chassis_id", "neighbor_interface_description",
        )
        remote_ref = normalize_device_id(remote_raw)
        if not remote_ref or remote_ref == asset_ref:
            continue

        local_port = _first(row, "local_interface", "local_port", "local_intf")
        remote_port = _first(
            row, "remote_interface", "neighbor_interface", "remote_port", "port_id"
        )
        management_ip = _first(
            row, "management_ip", "mgmt_address", "neighbor_ip", "ip_address", "mgmt_ip"
        )
        capabilities = _first(row, "capabilities", "capability") or ""

        neighbours.append(
            CollectedAsset(
                source_ref=remote_ref,
                name=remote_ref,
                type="network_device",
                criticality="medium",
                ip_address=management_ip,
                vendor=_first(row, "platform", "system_description"),
                model=_first(row, "platform"),
                description=f"Discovered over {protocol.upper()} from {asset_ref}",
                tags=["discovered", protocol],
                raw={"capabilities": capabilities},
            )
        )
        links.append(
            CollectedLink(
                source_ref=asset_ref,
                target_ref=remote_ref,
                link_type="CONNECTS_TO",
                source_interface=local_port,
                target_interface=remote_port,
                discovery_protocol=protocol.upper(),
            )
        )

    return neighbours, links


def parse_vlans(platform: str, output: str) -> dict[str, str]:
    """Map interface name to VLAN id from ``show vlan brief``."""
    command = COMMANDS.get(platform, {}).get("vlans", "")
    if not command:
        return {}
    mapping: dict[str, str] = {}
    for row in _textfsm_parse(platform, command, output):
        vlan_id = _first(row, "vlan_id", "vlan")
        interfaces = row.get("interfaces") or []
        if isinstance(interfaces, str):
            interfaces = [interfaces]
        for interface in interfaces:
            if vlan_id and interface:
                mapping[str(interface).strip()] = str(vlan_id)
    return mapping


def build_device_result(
    platform: str,
    host: str,
    outputs: dict[str, str],
    *,
    environment: str = "production",
    criticality: str = "high",
    owner: str | None = None,
) -> CollectionResult:
    """Assemble one device's collected state from its raw command outputs.

    Separated from the SSH transport so the whole assembly path can be tested
    against captured output with no device present.
    """
    result = CollectionResult(connector_key="ssh_network")

    version = parse_version(platform, outputs.get("version", ""), host)
    asset_ref = normalize_device_id(version["hostname"]) or normalize_device_id(host)

    interfaces = parse_interfaces(platform, outputs.get("interfaces", ""), asset_ref)
    vlan_map = parse_vlans(platform, outputs.get("vlans", ""))
    for interface in interfaces:
        if interface.name in vlan_map:
            interface.vlan_id = vlan_map[interface.name]

    management_ip = host
    for interface in interfaces:
        if interface.ip_address:
            management_ip = interface.ip_address
            break

    result.assets.append(
        CollectedAsset(
            source_ref=asset_ref,
            name=version["hostname"] or host,
            type="network_device",
            criticality=criticality,  # type: ignore[arg-type]
            environment=environment,
            owner=owner,
            ip_address=management_ip,
            vendor=VENDOR_BY_PLATFORM.get(platform),
            model=version["model"],
            os_name=version["os_name"],
            os_version=version["os_version"],
            serial_number=version["serial_number"],
            description=f"Collected over SSH from {host}",
            tags=["ssh", platform],
        )
    )
    result.interfaces.extend(interfaces)

    for protocol in ("cdp", "lldp"):
        neighbours, links = parse_neighbors(
            platform, outputs.get(protocol, ""), asset_ref, protocol
        )
        result.assets.extend(neighbours)
        result.links.extend(links)

    return result


# --------------------------------------------------------------------------
# Connector
# --------------------------------------------------------------------------

@register_connector
class SSHNetworkConnector(BaseConnector):
    key = "ssh_network"
    display_name = "Network devices over SSH"
    description = (
        "Collects inventory, interfaces and CDP/LLDP neighbors from routers, "
        "switches and firewalls."
    )
    category = "network"

    config_fields = (
        ConfigField(
            "hosts",
            "Device addresses",
            type="textarea",
            help="One permitted IP address or hostname per line, or comma-separated",
        ),
        ConfigField(
            "device_type",
            "Device type",
            type="select",
            choices=SUPPORTED_PLATFORMS,
            default="cisco_ios",
        ),
        ConfigField("username", "Username"),
        ConfigField("password", "Password", secret=True),
        ConfigField(
            "enable_secret",
            "Enable secret",
            secret=True,
            required=False,
        ),
        ConfigField("port", "Port", type="number", default=22, required=False),
        ConfigField(
            "verify_host_key", "Verify SSH host key", type="boolean",
            default=True, required=False,
            help="Keep enabled in production; trusted keys belong in the worker user's known_hosts file",
        ),
        ConfigField(
            "timeout", "Timeout (seconds)", type="number", default=30, required=False
        ),
        ConfigField(
            "environment", "Environment", default="production", required=False
        ),
        ConfigField(
            "criticality",
            "Criticality",
            type="select",
            choices=["low", "medium", "high", "critical"],
            default="high",
            required=False,
        ),
        ConfigField("owner", "Owner", required=False),
    )

    @staticmethod
    def _hosts(config: dict[str, Any]) -> list[str]:
        raw = config.get("hosts") or ""
        if isinstance(raw, list):
            candidates = raw
        else:
            candidates = str(raw).replace(",", "\n").splitlines()
        return [host.strip() for host in candidates if host.strip()]

    def validate_config(self, config: dict[str, Any]) -> None:
        super().validate_config(config)
        if not self._hosts(config):
            raise ConfigurationError("At least one device address is required")
        for host in self._hosts(config):
            try:
                validate_connector_target(host)
            except TargetPolicyError as exc:
                raise ConfigurationError(str(exc)) from exc
        platform = config.get("device_type", "cisco_ios")
        if platform not in SUPPORTED_PLATFORMS:
            raise ConfigurationError(
                f"Unsupported device type '{platform}'. Supported: {', '.join(SUPPORTED_PLATFORMS)}"
            )

    def _collect_host(
        self, host: str, platform: str, config: dict[str, Any]
    ) -> dict[str, str]:
        """Open one SSH session and capture every supported command's output."""
        from netmiko import ConnectHandler

        params = {
            "device_type": platform,
            "host": host,
            "username": config["username"],
            "password": config["password"],
            "port": int(config.get("port") or 22),
            "conn_timeout": int(config.get("timeout") or 30),
            "fast_cli": False,
            "ssh_strict": bool(config.get("verify_host_key", True)),
            "system_host_keys": bool(config.get("verify_host_key", True)),
        }
        if config.get("enable_secret"):
            params["secret"] = config["enable_secret"]

        outputs: dict[str, str] = {}
        with ConnectHandler(**params) as connection:
            if config.get("enable_secret"):
                try:
                    connection.enable()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Unable to enter enable mode on %s: %s", host, exc)
            for capability, command in COMMANDS.get(platform, {}).items():
                try:
                    outputs[capability] = connection.send_command(
                        command, read_timeout=int(config.get("timeout") or 30)
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Command '%s' failed on %s: %s", command, host, exc)
                    outputs[capability] = ""
        return outputs

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        config = self.apply_defaults(config)
        try:
            self.validate_config(config)
        except ConfigurationError as exc:
            return False, str(exc)

        host = self._hosts(config)[0]
        platform = config.get("device_type", "cisco_ios")
        try:
            from netmiko import ConnectHandler

            params = {
                "device_type": platform,
                "host": host,
                "username": config["username"],
                "password": config["password"],
                "port": int(config.get("port") or 22),
                "conn_timeout": int(config.get("timeout") or 15),
                "ssh_strict": bool(config.get("verify_host_key", True)),
                "system_host_keys": bool(config.get("verify_host_key", True)),
            }
            with ConnectHandler(**params) as connection:
                prompt = connection.find_prompt()
            return True, f"Connected to {host}; prompt: {prompt}"
        except Exception as exc:  # noqa: BLE001
            return False, f"Connection to {host} failed: {exc}"

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        config = self.apply_defaults(config)
        self.validate_config(config)

        platform = config.get("device_type", "cisco_ios")
        result = CollectionResult(connector_key=self.key)

        for host in self._hosts(config):
            try:
                outputs = self._collect_host(host, platform, config)
            except Exception as exc:  # noqa: BLE001 - one bad device must not end the run
                result.errors.append(f"{host}: {exc}")
                continue

            result.merge(
                build_device_result(
                    platform,
                    host,
                    outputs,
                    environment=config.get("environment", "production"),
                    criticality=config.get("criticality", "high"),
                    owner=config.get("owner"),
                )
            )

        return result
