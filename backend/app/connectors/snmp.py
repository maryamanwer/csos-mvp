"""SNMP connector for devices that cannot or should not be reached over SSH.

Reads the standard MIB-II system group and interface table, plus the LLDP
remote-systems table when the device exposes it. SNMPv2c and SNMPv3 are both
supported; v3 with authPriv is the only version appropriate for a production
network, and v2c is offered because a great deal of installed equipment still
speaks nothing else.

Walking is read-only. No SET operation exists anywhere in this connector.
"""
from __future__ import annotations

import asyncio
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
from app.connectors.ssh_network import normalize_device_id
from app.core.network_policy import TargetPolicyError, validate_connector_target

logger = logging.getLogger(__name__)

# MIB-II system group
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"

# Interface table
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_TYPE = "1.3.6.1.2.1.2.2.1.3"
OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
OID_IF_PHYS_ADDRESS = "1.3.6.1.2.1.2.2.1.6"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"

# IP address table — maps an address to its interface index and mask
OID_IP_AD_ENT_IF_INDEX = "1.3.6.1.2.1.4.20.1.2"
OID_IP_AD_ENT_NETMASK = "1.3.6.1.2.1.4.20.1.3"

# LLDP remote systems
OID_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"
OID_LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"

IF_OPER_STATUS = {"1": "up", "2": "down", "3": "testing", "4": "unknown"}

VENDOR_BY_ENTERPRISE = {
    "9": "Cisco",
    "2636": "Juniper",
    "30065": "Arista",
    "12356": "Fortinet",
    "25461": "Palo Alto Networks",
    "11": "HP",
    "674": "Dell",
    "1991": "Brocade",
    "6027": "Dell Force10",
    "8072": "Net-SNMP",
    "311": "Microsoft",
    "2021": "Linux (UCD-SNMP)",
}


def vendor_from_sys_object_id(sys_object_id: str | None) -> str | None:
    """Map ``1.3.6.1.4.1.<enterprise>...`` to a vendor name."""
    if not sys_object_id:
        return None
    marker = "1.3.6.1.4.1."
    text = str(sys_object_id)
    if marker not in text:
        return None
    remainder = text.split(marker, 1)[1]
    enterprise = remainder.split(".", 1)[0]
    return VENDOR_BY_ENTERPRISE.get(enterprise)


def classify_from_sys_descr(sys_descr: str | None) -> str:
    """Best-effort asset type from the device's own self-description."""
    text = (sys_descr or "").lower()
    network_markers = (
        "cisco ios", "nx-os", "junos", "arista", "switch", "router",
        "fortigate", "pan-os", "procurve", "routeros", "firewall",
    )
    if any(marker in text for marker in network_markers):
        return "network_device"
    if "windows" in text or "linux" in text or "ubuntu" in text or "centos" in text:
        return "server"
    return "network_device"


def _decode(value: Any) -> str:
    """SNMP octet strings arrive as bytes or pyasn1 objects; normalize to str."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _format_mac(value: Any) -> str | None:
    raw = value
    try:
        if hasattr(raw, "asOctets"):
            raw = raw.asOctets()
        if isinstance(raw, bytes) and len(raw) == 6:
            return ":".join(f"{byte:02x}" for byte in raw)
    except Exception:  # noqa: BLE001
        pass
    text = _decode(value)
    return text or None


def build_snmp_result(
    host: str,
    system: dict[str, str],
    interface_rows: dict[str, dict[str, Any]],
    lldp_neighbours: list[dict[str, str]],
    *,
    environment: str = "production",
    criticality: str = "medium",
    owner: str | None = None,
) -> CollectionResult:
    """Assemble a device from already-walked SNMP data.

    Kept free of any network access so the assembly logic is unit-testable.
    """
    result = CollectionResult(connector_key="snmp")

    sys_name = system.get("sys_name") or host
    asset_ref = normalize_device_id(sys_name) or normalize_device_id(host)
    sys_descr = system.get("sys_descr")

    interfaces: list[CollectedInterface] = []
    for row in interface_rows.values():
        name = row.get("name")
        if not name:
            continue
        speed_bps = row.get("speed")
        speed = None
        if speed_bps:
            try:
                speed = f"{int(speed_bps) // 1_000_000} Mbps"
            except (TypeError, ValueError):
                speed = None
        interfaces.append(
            CollectedInterface(
                asset_ref=asset_ref,
                name=str(name),
                ip_address=row.get("ip_address"),
                subnet_cidr=row.get("subnet_cidr"),
                mac_address=row.get("mac_address"),
                status=row.get("status"),
                speed=speed,
                description=row.get("description"),
            )
        )

    management_ip = host
    for interface in interfaces:
        if interface.ip_address and not interface.ip_address.startswith("127."):
            management_ip = interface.ip_address
            break

    result.assets.append(
        CollectedAsset(
            source_ref=asset_ref,
            name=sys_name,
            type=classify_from_sys_descr(sys_descr),  # type: ignore[arg-type]
            criticality=criticality,  # type: ignore[arg-type]
            environment=environment,
            owner=owner,
            ip_address=management_ip,
            vendor=vendor_from_sys_object_id(system.get("sys_object_id")),
            os_name=(sys_descr or "").split(",")[0][:120] or None,
            location=system.get("sys_location"),
            description=f"Collected over SNMP from {host}",
            tags=["snmp"],
            raw={"sys_descr": sys_descr or ""},
        )
    )
    result.interfaces.extend(interfaces)

    for neighbour in lldp_neighbours:
        remote_ref = normalize_device_id(neighbour.get("sys_name"))
        if not remote_ref or remote_ref == asset_ref:
            continue
        result.assets.append(
            CollectedAsset(
                source_ref=remote_ref,
                name=remote_ref,
                type="network_device",
                description=f"Discovered over LLDP from {asset_ref}",
                tags=["discovered", "lldp"],
            )
        )
        result.links.append(
            CollectedLink(
                source_ref=asset_ref,
                target_ref=remote_ref,
                link_type="CONNECTS_TO",
                target_interface=neighbour.get("port_id"),
                discovery_protocol="LLDP",
            )
        )

    return result


@register_connector
class SNMPConnector(BaseConnector):
    key = "snmp"
    display_name = "Network devices over SNMP"
    description = (
        "Collects system inventory, interfaces and LLDP neighbors using read-only SNMP."
    )
    category = "network"

    config_fields = (
        ConfigField(
            "hosts", "Device addresses", type="textarea",
            help="One permitted address per line, or comma-separated",
        ),
        ConfigField(
            "version", "SNMP version", type="select",
            choices=["3", "2c"], default="3",
        ),
        ConfigField(
            "community", "Read community (v2c)", secret=True, required=False,
        ),
        ConfigField("v3_user", "SNMPv3 username", required=False),
        ConfigField("v3_auth_key", "SNMPv3 authentication key", secret=True, required=False),
        ConfigField("v3_priv_key", "SNMPv3 privacy key", secret=True, required=False),
        ConfigField(
            "v3_auth_protocol", "Authentication protocol", type="select",
            choices=["SHA", "SHA256", "SHA512", "MD5"], default="SHA256",
            required=False,
        ),
        ConfigField(
            "v3_priv_protocol", "Privacy protocol", type="select",
            choices=["AES", "AES256", "DES"], default="AES", required=False,
        ),
        ConfigField("port", "Port", type="number", default=161, required=False),
        ConfigField("timeout", "Timeout (seconds)", type="number", default=5, required=False),
        ConfigField("environment", "Environment", default="production", required=False),
        ConfigField(
            "criticality", "Criticality", type="select",
            choices=["low", "medium", "high", "critical"],
            default="medium", required=False,
        ),
        ConfigField("owner", "Owner", required=False),
    )

    @staticmethod
    def _hosts(config: dict[str, Any]) -> list[str]:
        raw = config.get("hosts") or ""
        candidates = raw if isinstance(raw, list) else str(raw).replace(",", "\n").splitlines()
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
        if str(config.get("version", "3")) == "3":
            if not config.get("v3_user"):
                raise ConfigurationError("SNMPv3 requires a username")
            if not config.get("v3_auth_key") or not config.get("v3_priv_key"):
                raise ConfigurationError(
                    "SNMPv3 requires authentication and privacy keys (authPriv)"
                )
        elif not config.get("community"):
            raise ConfigurationError("SNMPv2c requires a read community")

    def _auth_data(self, config: dict[str, Any]):
        from pysnmp.hlapi.v3arch.asyncio import (
            USM_AUTH_HMAC96_MD5,
            USM_AUTH_HMAC96_SHA,
            USM_AUTH_HMAC192_SHA256,
            USM_AUTH_HMAC384_SHA512,
            USM_PRIV_CBC56_DES,
            USM_PRIV_CFB128_AES,
            USM_PRIV_CFB256_AES,
            CommunityData,
            UsmUserData,
        )

        if str(config.get("version", "3")) != "3":
            return CommunityData(config["community"], mpModel=1)

        auth_map = {
            "MD5": USM_AUTH_HMAC96_MD5,
            "SHA": USM_AUTH_HMAC96_SHA,
            "SHA256": USM_AUTH_HMAC192_SHA256,
            "SHA512": USM_AUTH_HMAC384_SHA512,
        }
        priv_map = {
            "DES": USM_PRIV_CBC56_DES,
            "AES": USM_PRIV_CFB128_AES,
            "AES256": USM_PRIV_CFB256_AES,
        }
        return UsmUserData(
            config["v3_user"],
            authKey=config.get("v3_auth_key") or None,
            privKey=config.get("v3_priv_key") or None,
            authProtocol=auth_map.get(config.get("v3_auth_protocol", "SHA256")),
            privProtocol=priv_map.get(config.get("v3_priv_protocol", "AES")),
        )

    async def _walk_host(self, host: str, config: dict[str, Any]) -> dict[str, Any]:
        from pysnmp.hlapi.v3arch.asyncio import (
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            get_cmd,
            walk_cmd,
        )

        engine = SnmpEngine()
        auth = self._auth_data(config)
        target = await UdpTransportTarget.create(
            (host, int(config.get("port") or 161)),
            timeout=int(config.get("timeout") or 5),
            retries=1,
        )
        context = ContextData()

        async def get(oid: str) -> str:
            error_indication, error_status, _, var_binds = await get_cmd(
                engine, auth, target, context, ObjectType(ObjectIdentity(oid))
            )
            if error_indication or error_status:
                return ""
            return _decode(var_binds[0][1]) if var_binds else ""

        async def walk(oid: str) -> dict[str, Any]:
            values: dict[str, Any] = {}
            async for error_indication, error_status, _, var_binds in walk_cmd(
                engine, auth, target, context, ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False,
            ):
                if error_indication or error_status:
                    break
                for name, value in var_binds:
                    index = str(name).replace(f"{oid}.", "", 1)
                    values[index] = value
            return values

        system = {
            "sys_descr": await get(OID_SYS_DESCR),
            "sys_object_id": await get(OID_SYS_OBJECT_ID),
            "sys_name": await get(OID_SYS_NAME),
            "sys_location": await get(OID_SYS_LOCATION),
        }
        if not any(system.values()):
            raise ConnectionError("No SNMP response from device")

        descriptions = await walk(OID_IF_DESCR)
        statuses = await walk(OID_IF_OPER_STATUS)
        speeds = await walk(OID_IF_SPEED)
        macs = await walk(OID_IF_PHYS_ADDRESS)
        aliases = await walk(OID_IF_ALIAS)
        ip_if_index = await walk(OID_IP_AD_ENT_IF_INDEX)
        ip_netmask = await walk(OID_IP_AD_ENT_NETMASK)

        interfaces: dict[str, dict[str, Any]] = {}
        for index, description in descriptions.items():
            interfaces[index] = {
                "name": _decode(description),
                "status": IF_OPER_STATUS.get(_decode(statuses.get(index)), None),
                "speed": _decode(speeds.get(index)) or None,
                "mac_address": _format_mac(macs.get(index)),
                "description": _decode(aliases.get(index)) or None,
            }

        from app.connectors.ssh_network import derive_cidr

        for address, index_value in ip_if_index.items():
            index = _decode(index_value)
            if index in interfaces:
                interfaces[index]["ip_address"] = address
                interfaces[index]["subnet_cidr"] = derive_cidr(
                    address, _decode(ip_netmask.get(address))
                )

        lldp_names = await walk(OID_LLDP_REM_SYS_NAME)
        lldp_ports = await walk(OID_LLDP_REM_PORT_ID)
        neighbours = [
            {"sys_name": _decode(value), "port_id": _decode(lldp_ports.get(index))}
            for index, value in lldp_names.items()
        ]

        return {"system": system, "interfaces": interfaces, "lldp": neighbours}

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        config = self.apply_defaults(config)
        try:
            self.validate_config(config)
        except ConfigurationError as exc:
            return False, str(exc)
        host = self._hosts(config)[0]
        try:
            data = asyncio.run(self._walk_host(host, config))
            name = data["system"].get("sys_name") or "unnamed"
            return True, f"Connected to {host}; sysName: {name}"
        except Exception as exc:  # noqa: BLE001
            return False, f"Connection to {host} failed: {exc}"

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        config = self.apply_defaults(config)
        self.validate_config(config)

        result = CollectionResult(connector_key=self.key)
        for host in self._hosts(config):
            try:
                data = asyncio.run(self._walk_host(host, config))
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"{host}: {exc}")
                continue
            result.merge(
                build_snmp_result(
                    host,
                    data["system"],
                    data["interfaces"],
                    data["lldp"],
                    environment=config.get("environment", "production"),
                    criticality=config.get("criticality", "medium"),
                    owner=config.get("owner"),
                )
            )
        return result
