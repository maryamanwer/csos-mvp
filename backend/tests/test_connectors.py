"""Behavior checks for the CSOS-native evidence pipeline."""
from __future__ import annotations

import pytest

from app.connectors import get_connector, registered_keys
from app.connectors.agent_ingest import normalize_agent_payload
from app.connectors.base import ConfigurationError, ConnectorError
from app.connectors.models import CollectedAsset, CollectedLink, CollectedVulnerability, CollectionResult
from app.connectors.nmap_scan import parse_nmap_xml
from app.connectors.snmp import build_snmp_result, vendor_from_sys_object_id
from app.connectors.ssh_network import build_device_result, derive_cidr, normalize_device_id
from app.connectors.syslog import decode_priority, events_to_result, parse_syslog_line
from app.core.secrets import decrypt_config, decrypt_secret, encrypt_config, encrypt_secret, generate_api_key, hash_api_key, redact_config


def test_source_catalogue_contains_pull_and_push_adapters():
    assert {"ssh_network", "snmp", "nmap", "agent", "syslog"} <= set(registered_keys())
    assert get_connector("agent").schedulable is False
    with pytest.raises(ConnectorError):
        get_connector("missing")


def test_source_configuration_is_validated_and_defaulted():
    adapter = get_connector("ssh_network")
    with pytest.raises(ConfigurationError):
        adapter.validate_config({"hosts": "10.8.0.1"})
    ready = adapter.apply_defaults({"hosts": "10.8.0.1", "username": "ops", "password": "secret"})
    assert ready["port"] == 22


@pytest.mark.parametrize("value,expected", [
    ("branch-rtr-02.example.net", "BRANCH-RTR-02"),
    ("dist-sw-03(SERIAL)", "DIST-SW-03"),
    (None, ""),
])
def test_network_identity_normalization(value, expected):
    assert normalize_device_id(value) == expected


@pytest.mark.parametrize("address,prefix,expected", [
    ("172.16.40.12", "24", "172.16.40.0/24"),
    ("172.16.40.12", "255.255.255.0", "172.16.40.0/24"),
    ("bad", "24", None),
])
def test_subnet_derivation(address, prefix, expected):
    assert derive_cidr(address, prefix) == expected


def test_cli_observations_become_assets_interfaces_and_links():
    output = {
        "version": "Cisco IOS Software, Version 17.6.4, RELEASE\nBRANCH-RTR-01 uptime is 2 days\nCisco ISR4331 (1RU) processor\nProcessor board ID FGL00000001",
        "interfaces": "Interface IP-Address OK? Method Status Protocol\nGigabitEthernet0/0 172.16.40.1 YES manual up up\nLoopback0 unassigned YES unset up up",
        "cdp": "-------------------------\nDevice ID: DIST-SW-03.example.net\nIP address: 172.16.40.2\nPlatform: cisco C9300, Capabilities: Switch\nInterface: GigabitEthernet0/0, Port ID (outgoing port): GigabitEthernet1/0/48\n",
    }
    evidence = build_device_result("cisco_ios", "172.16.40.1", output)
    assert evidence.assets[0].source_ref == "BRANCH-RTR-01"
    assert evidence.assets[0].model == "ISR4331"
    assert {item.name for item in evidence.interfaces} == {"GigabitEthernet0/0", "Loopback0"}
    assert evidence.links[0].target_ref == "DIST-SW-03"


def test_snmp_observation_uses_enterprise_identity_and_lldp():
    evidence = build_snmp_result(
        "172.16.50.2",
        {"sys_name": "ACCESS-02.example.net", "sys_descr": "Cisco IOS switch", "sys_object_id": "1.3.6.1.4.1.9.1.516", "sys_location": "Floor 3"},
        {"7": {"name": "Gi1/0/7", "status": "up", "speed": "1000000000"}},
        [{"sys_name": "DIST-01", "port_id": "Gi0/7"}],
    )
    assert vendor_from_sys_object_id("1.3.6.1.4.1.9.1.516") == "Cisco"
    assert evidence.assets[0].location == "Floor 3"
    assert evidence.interfaces[0].speed == "1000 Mbps"
    assert evidence.links[0].discovery_protocol == "LLDP"


def test_syslog_parsing_preserves_sender_and_unrecognized_messages():
    event = parse_syslog_line("<34>Nov 02 08:10:01 access-02 Interface Gi1/0/7 down", "172.16.50.2")
    assert (event.hostname, event.facility, event.severity) == ("access-02", "auth", "critical")
    raw = parse_syslog_line("vendor-specific message", "172.16.50.2")
    assert raw.message == "vendor-specific message"
    assert decode_priority(13) == ("user", "notice")
    assert len(events_to_result([event, event]).assets) == 1


def test_endpoint_report_correlates_inventory_and_exposure():
    evidence = normalize_agent_payload({
        "agent_id": "endpoint-22", "hostname": "finance-app-02.example.net",
        "criticality": "critical", "system": {"os_name": "Linux", "vendor": "Lenovo"},
        "network": {"interfaces": [{"name": "ens192", "ip_address": "172.16.60.22", "subnet_cidr": "172.16.60.0/24"}]},
        "listening_ports": [{"port": 23, "address": "0.0.0.0"}, {"port": 6379, "address": "127.0.0.1"}],
    })
    assert evidence.assets[0].source_ref == "FINANCE-APP-02"
    assert {finding.port for finding in evidence.vulnerabilities} == {23}
    assert evidence.vulnerabilities[0].severity == "critical"


def test_nmap_import_skips_down_hosts_and_flags_database_exposure():
    xml = """<nmaprun><host><status state='up'/><address addr='172.16.70.9' addrtype='ipv4'/><hostnames><hostname name='orders-db-02.example.net'/></hostnames><ports><port protocol='tcp' portid='5432'><state state='open'/><service name='postgresql' product='PostgreSQL' version='16.2'/></port></ports><os><osmatch name='Linux 6'/></os></host><host><status state='down'/><address addr='172.16.70.10' addrtype='ipv4'/></host></nmaprun>"""
    evidence = parse_nmap_xml(xml)
    assert [asset.source_ref for asset in evidence.assets] == ["ORDERS-DB-02"]
    assert evidence.vulnerabilities[0].port == 5432
    assert "PostgreSQL 16.2" in evidence.vulnerabilities[0].description
    assert parse_nmap_xml("<broken").errors


def test_credential_envelope_and_api_key_hashing():
    encrypted = encrypt_secret("network-password")
    assert encrypted.startswith("enc:v1:") and "network-password" not in encrypted
    assert decrypt_secret(encrypted) == "network-password"
    stored = encrypt_config({"username": "ops", "password": "network-password"}, {"password"})
    assert decrypt_config(stored, {"password"})["password"] == "network-password"
    assert redact_config(stored, {"password"})["password"] == "••••••••"
    key = generate_api_key()
    assert key.startswith("csos_") and hash_api_key(key) == hash_api_key(key)


class RecordingGraph:
    def __init__(self, trust: int | None = None):
        self.trust = trust
        self.calls: list[tuple[str, dict]] = []

    def run(self, query, parameters=None):
        parameters = parameters or {}
        self.calls.append((" ".join(query.split()), parameters))
        if query.startswith("MATCH (a:Asset {source_ref: $source_ref}) RETURN"):
            return [] if self.trust is None else [{"id": "asset-existing", "confidence": self.trust}]
        if "RETURN a.id AS id" in query:
            return [{"id": "asset-created"}]
        if "RETURN i.id AS id" in query:
            return [{"id": "interface-created"}]
        if "RETURN rel.id AS id" in query:
            return [{"id": "relationship-created"}]
        if "RETURN v.id AS id" in query:
            return [{"id": "finding-created"}]
        return []


def test_graph_writer_is_idempotent_and_refuses_relationship_injection():
    from app.graph.network_writer import NetworkGraphWriter

    graph = RecordingGraph()
    result = CollectionResult(connector_key="nmap", assets=[CollectedAsset(source_ref="ORDERS-DB-02", name="orders-db-02")])
    assert NetworkGraphWriter(graph).write(result)["assets"] == 1
    unsafe = CollectionResult(connector_key="nmap", links=[CollectedLink(source_ref="A", target_ref="B")])
    unsafe.links[0].link_type = "DELETE"  # type: ignore[assignment]
    assert NetworkGraphWriter(graph).upsert_links(unsafe) == 0
    assert unsafe.errors


def test_vendor_finding_identity_is_source_scoped():
    from app.graph.network_writer import NetworkGraphWriter

    graph = RecordingGraph()
    result = CollectionResult(connector_key="edr_xdr_api", vulnerabilities=[CollectedVulnerability(title="Endpoint alert", vendor_finding_id="case-992")])
    NetworkGraphWriter(graph).upsert_vulnerabilities(result)
    call = next(parameters for query, parameters in graph.calls if "MERGE (v:Vulnerability" in query)
    assert call["identity"] == "edr_xdr_api:case-992"
