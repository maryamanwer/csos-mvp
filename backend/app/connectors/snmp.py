"""Read-only SNMP evidence adapter for CSOS-managed network ranges."""
from __future__ import annotations

import asyncio
from typing import Any

from app.connectors.base import BaseConnector, ConfigField, ConfigurationError, register_connector
from app.connectors.models import CollectedAsset, CollectedInterface, CollectedLink, CollectionResult
from app.connectors.ssh_network import derive_cidr, normalize_device_id
from app.core.network_policy import TargetPolicyError, validate_connector_target

_ENTERPRISES = {
    "1.3.6.1.4.1.9.": "Cisco",
    "1.3.6.1.4.1.2636.": "Juniper",
    "1.3.6.1.4.1.12356.": "Fortinet",
    "1.3.6.1.4.1.8072.": "Net-SNMP",
}


def vendor_from_sys_object_id(sys_object_id: str | None) -> str | None:
    value = str(sys_object_id or "").lstrip(".")
    return next((vendor for prefix, vendor in _ENTERPRISES.items() if value.startswith(prefix)), None)


def classify_from_sys_descr(sys_descr: str | None) -> str:
    text = (sys_descr or "").lower()
    if any(word in text for word in ("cisco", "junos", "juniper", "fortios", "switch", "router")):
        return "network_device"
    return "server"


def _speed_label(value: Any) -> str | None:
    try:
        bits = int(str(value))
    except (TypeError, ValueError):
        return None
    if bits >= 1_000_000_000:
        return f"{bits // 1_000_000} Mbps"
    if bits >= 1_000_000:
        return f"{bits // 1_000_000} Mbps"
    return f"{bits} bps"


def build_snmp_result(
    host: str,
    system: dict[str, Any],
    interfaces: dict[str, dict[str, Any]],
    neighbours: list[dict[str, Any]],
    *,
    environment: str = "production",
    criticality: str = "medium",
    owner: str | None = None,
) -> CollectionResult:
    result = CollectionResult(connector_key="snmp")
    display_name = str(system.get("sys_name") or host)
    ref = normalize_device_id(display_name) or normalize_device_id(host)
    result.assets.append(CollectedAsset(
        source_ref=ref, name=display_name, hostname=display_name,
        ip_address=host, type=classify_from_sys_descr(system.get("sys_descr")),
        criticality=criticality, environment=environment, owner=owner,
        vendor=vendor_from_sys_object_id(system.get("sys_object_id")),
        location=system.get("sys_location"), description=system.get("sys_descr"),
        data_sources=["SNMP"], tags=["snmp"],
    ))
    for item in interfaces.values():
        if not item.get("name"):
            continue
        result.interfaces.append(CollectedInterface(
            asset_ref=ref, name=str(item["name"]), ip_address=item.get("ip_address"),
            subnet_cidr=item.get("subnet_cidr"), mac_address=item.get("mac_address"),
            status=item.get("status"), speed=_speed_label(item.get("speed")),
            description=item.get("description"), vlan_id=item.get("vlan_id"),
        ))
    seen: set[str] = set()
    for neighbour in neighbours:
        remote = normalize_device_id(neighbour.get("sys_name"))
        if not remote or remote == ref:
            continue
        if remote not in seen:
            result.assets.append(CollectedAsset(
                source_ref=remote, name=remote, type="network_device",
                description=f"Observed through LLDP from {ref}", tags=["discovered", "lldp"],
            ))
            seen.add(remote)
        result.links.append(CollectedLink(
            source_ref=ref, target_ref=remote,
            source_interface=neighbour.get("local_port"), target_interface=neighbour.get("port_id"),
            discovery_protocol="LLDP",
        ))
    return result


@register_connector
class SNMPConnector(BaseConnector):
    key = "snmp"
    display_name = "SNMP inventory"
    description = "Reads system, interface and LLDP evidence using SNMPv3 or approved SNMPv2c."
    category = "network"
    config_fields = (
        ConfigField("hosts", "Device addresses", type="textarea"),
        ConfigField("version", "SNMP version", type="select", choices=["3", "2c"], default="3"),
        ConfigField("community", "Read community (v2c)", required=False, secret=True),
        ConfigField("v3_user", "SNMPv3 username", required=False),
        ConfigField("v3_auth_key", "SNMPv3 authentication key", required=False, secret=True),
        ConfigField("v3_priv_key", "SNMPv3 privacy key", required=False, secret=True),
        ConfigField("v3_auth_protocol", "Authentication protocol", type="select", choices=["SHA", "SHA256", "SHA512", "MD5"], required=False, default="SHA256"),
        ConfigField("v3_priv_protocol", "Privacy protocol", type="select", choices=["AES", "AES256", "DES"], required=False, default="AES"),
        ConfigField("port", "Port", type="number", required=False, default=161),
        ConfigField("timeout", "Timeout (seconds)", type="number", required=False, default=5),
        ConfigField("environment", "Environment", required=False, default="production"),
        ConfigField("criticality", "Criticality", type="select", choices=["low", "medium", "high", "critical"], required=False, default="medium"),
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
        for host in hosts:
            try:
                validate_connector_target(host)
            except TargetPolicyError as error:
                raise ConfigurationError(str(error)) from error
        if str(config.get("version", "3")) == "3":
            if not all(config.get(name) for name in ("v3_user", "v3_auth_key", "v3_priv_key")):
                raise ConfigurationError("SNMPv3 requires username, authentication key and privacy key")
        elif not config.get("community"):
            raise ConfigurationError("SNMPv2c requires a read community")

    async def _read_host(self, host: str, config: dict[str, Any]) -> dict[str, Any]:
        """Read standards-based system, interface, address and LLDP tables."""
        from pysnmp.hlapi.v3arch.asyncio import (
            USM_AUTH_HMAC96_MD5, USM_AUTH_HMAC96_SHA, USM_AUTH_HMAC192_SHA256,
            USM_AUTH_HMAC384_SHA512, USM_PRIV_CBC56_DES, USM_PRIV_CFB128_AES,
            USM_PRIV_CFB256_AES, CommunityData, ContextData, ObjectIdentity,
            ObjectType, SnmpEngine, UdpTransportTarget, UsmUserData, get_cmd,
            walk_cmd,
        )
        if str(config.get("version", "3")) == "3":
            auth_protocols = {
                "MD5": USM_AUTH_HMAC96_MD5, "SHA": USM_AUTH_HMAC96_SHA,
                "SHA256": USM_AUTH_HMAC192_SHA256, "SHA512": USM_AUTH_HMAC384_SHA512,
            }
            privacy_protocols = {
                "DES": USM_PRIV_CBC56_DES, "AES": USM_PRIV_CFB128_AES,
                "AES256": USM_PRIV_CFB256_AES,
            }
            auth = UsmUserData(
                config["v3_user"], authKey=config["v3_auth_key"], privKey=config["v3_priv_key"],
                authProtocol=auth_protocols[config.get("v3_auth_protocol", "SHA256")],
                privProtocol=privacy_protocols[config.get("v3_priv_protocol", "AES")],
            )
        else:
            auth = CommunityData(config["community"], mpModel=1)
        target = await UdpTransportTarget.create(
            (host, int(config.get("port", 161))), timeout=int(config.get("timeout", 5)), retries=1,
        )
        oids = {
            "sys_descr": "1.3.6.1.2.1.1.1.0", "sys_object_id": "1.3.6.1.2.1.1.2.0",
            "sys_name": "1.3.6.1.2.1.1.5.0", "sys_location": "1.3.6.1.2.1.1.6.0",
        }
        result: dict[str, Any] = {}
        engine = SnmpEngine()
        context = ContextData()
        for name, oid in oids.items():
            error, status, _, bindings = await get_cmd(
                engine, auth, target, context, ObjectType(ObjectIdentity(oid)),
            )
            if error or status:
                result[name] = ""
            else:
                result[name] = str(bindings[0][1]) if bindings else ""
        if not any(result.values()):
            raise ConnectionError("Device returned no SNMP system values")

        async def walk(oid: str) -> dict[str, str]:
            values: dict[str, str] = {}
            async for error, status, _, bindings in walk_cmd(
                engine, auth, target, context, ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False,
            ):
                if error or status:
                    break
                for name, value in bindings:
                    full_name = str(name)
                    suffix = full_name[len(oid) + 1:] if full_name.startswith(oid + ".") else full_name
                    values[suffix] = str(value)
            return values

        descriptions = await walk("1.3.6.1.2.1.2.2.1.2")
        operational = await walk("1.3.6.1.2.1.2.2.1.8")
        speeds = await walk("1.3.6.1.2.1.2.2.1.5")
        physical = await walk("1.3.6.1.2.1.2.2.1.6")
        aliases = await walk("1.3.6.1.2.1.31.1.1.1.18")
        address_index = await walk("1.3.6.1.2.1.4.20.1.2")
        masks = await walk("1.3.6.1.2.1.4.20.1.3")

        interfaces: dict[str, dict[str, Any]] = {}
        for index, description in descriptions.items():
            interfaces[index] = {
                "name": description,
                "status": "up" if operational.get(index) == "1" else "down",
                "speed": speeds.get(index),
                "mac_address": physical.get(index) or None,
                "description": aliases.get(index) or None,
            }
        for address, index in address_index.items():
            if index in interfaces:
                interfaces[index]["ip_address"] = address
                interfaces[index]["subnet_cidr"] = derive_cidr(address, masks.get(address))

        lldp_names = await walk("1.0.8802.1.1.2.1.4.1.1.9")
        lldp_ports = await walk("1.0.8802.1.1.2.1.4.1.1.7")
        neighbours = [
            {"sys_name": name, "port_id": lldp_ports.get(index)}
            for index, name in lldp_names.items() if name
        ]
        return {"system": result, "interfaces": interfaces, "lldp": neighbours}

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        ready = self.apply_defaults(config)
        try:
            self.validate_config(ready)
            host = self._hosts(ready)[0]
            data = asyncio.run(self._read_host(host, ready))
            return True, f"Connected to {host}; sysName: {data['system'].get('sys_name') or 'unnamed'}"
        except Exception as error:
            return False, str(error)

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        ready = self.apply_defaults(config)
        self.validate_config(ready)
        aggregate = CollectionResult(connector_key=self.key)
        for host in self._hosts(ready):
            try:
                data = asyncio.run(self._read_host(host, ready))
                aggregate.merge(build_snmp_result(
                    host, data["system"], data["interfaces"], data["lldp"],
                    environment=ready.get("environment", "production"),
                    criticality=ready.get("criticality", "medium"), owner=ready.get("owner"),
                ))
            except Exception as error:
                aggregate.errors.append(f"{host}: {error}")
        return aggregate
