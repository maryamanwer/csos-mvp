"""Tests for the collection layer.

Parsing is exercised against captured device output rather than a live device,
so the whole ingestion path is verifiable in CI with no lab attached. The graph
writer is tested against a recording fake, which lets the correlation and
confidence rules be asserted precisely — those rules are what stop the same
router appearing three times, and they are worth pinning down.
"""
from __future__ import annotations

import pytest

from app.connectors import get_connector, list_connectors, registered_keys
from app.connectors.agent_ingest import normalize_agent_payload
from app.connectors.base import ConfigurationError, ConnectorError
from app.connectors.models import (
    CollectedAsset,
    CollectedLink,
    CollectedVulnerability,
    CollectionResult,
)
from app.connectors.nmap_scan import parse_nmap_xml
from app.connectors.snmp import (
    build_snmp_result,
    classify_from_sys_descr,
    vendor_from_sys_object_id,
)
from app.connectors.ssh_network import (
    build_device_result,
    derive_cidr,
    normalize_device_id,
)
from app.connectors.syslog import decode_priority, events_to_result, parse_syslog_line
from app.core.secrets import (
    decrypt_config,
    decrypt_secret,
    encrypt_config,
    encrypt_secret,
    generate_api_key,
    hash_api_key,
    redact_config,
)


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

class TestRegistry:
    def test_all_builtin_connectors_are_registered(self):
        keys = set(registered_keys())
        assert {"ssh_network", "snmp", "syslog", "agent", "nmap"} <= keys

    def test_every_connector_describes_itself(self):
        for described in list_connectors():
            assert described["key"]
            assert described["display_name"]
            assert described["category"]
            assert isinstance(described["config_fields"], list)

    def test_unknown_connector_is_rejected(self):
        with pytest.raises(ConnectorError):
            get_connector("does_not_exist")

    def test_push_connectors_are_not_schedulable(self):
        for key in ("syslog", "agent"):
            assert get_connector(key).schedulable is False

    def test_missing_required_field_is_reported(self):
        with pytest.raises(ConfigurationError):
            get_connector("ssh_network").validate_config({"hosts": "10.0.0.1"})


# --------------------------------------------------------------------------
# SSH / network devices
# --------------------------------------------------------------------------

SHOW_VERSION = """Cisco IOS Software, 7200 Software (C7200-ADVENTERPRISEK9-M), Version 15.2(4)S5, RELEASE SOFTWARE (fc1)

R1 uptime is 3 hours, 12 minutes
System image file is "tftp://255.255.255.255/unknown"

Cisco 7206VXR (NPE400) processor (revision A) with 491520K/32768K bytes of memory.
Processor board ID 4279256517
Configuration register is 0x2102
"""

SHOW_IP_INT_BRIEF = """Interface                  IP-Address      OK? Method Status                Protocol
FastEthernet0/0            10.0.10.1       YES NVRAM  up                    up
FastEthernet0/1            10.0.20.1       YES NVRAM  up                    up
Serial1/0                  unassigned      YES NVRAM  administratively down down
Loopback0                  192.168.1.1     YES NVRAM  up                    up
"""

# Captured verbatim from a device. The trailing "Version :" block matters:
# it is what terminates each CDP record, and a fixture trimmed without it
# silently parses as one neighbour instead of two.
SHOW_CDP_DETAIL = """-------------------------
Device ID: R2.corp.example.com
Entry address(es):
  IP address: 10.0.10.2
Platform: Cisco 7206VXR,  Capabilities: Router
Interface: FastEthernet0/0,  Port ID (outgoing port): FastEthernet0/0
Holdtime : 143 sec

Version :
Cisco IOS Software, 7200 Software (C7200-ADVENTERPRISEK9-M), Version 15.2(4)S5

advertisement version: 2

-------------------------
Device ID: SW1
Entry address(es):
  IP address: 10.0.20.5
Platform: cisco WS-C3560,  Capabilities: Switch IGMP
Interface: FastEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/1
Holdtime : 122 sec

Version :
Cisco IOS Software, C3560 Software (C3560-IPSERVICESK9-M), Version 12.2(55)SE

advertisement version: 2
"""


class TestDeviceIdNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("R2.corp.example.com", "R2"),
            ("R2", "R2"),
            ("SW1(FDO1234ABC)", "SW1"),
            ("core-sw-01.riyadh.local", "CORE-SW-01"),
            ("  r1  ", "R1"),
            (None, ""),
            ("", ""),
        ],
    )
    def test_variants_collapse_to_one_reference(self, raw, expected):
        """The same device named four ways must correlate to one node."""
        assert normalize_device_id(raw) == expected


class TestCidrDerivation:
    @pytest.mark.parametrize(
        "ip,prefix,expected",
        [
            ("10.0.10.1", "24", "10.0.10.0/24"),
            ("10.0.10.1", "255.255.255.0", "10.0.10.0/24"),
            ("192.168.1.1", "32", "192.168.1.1/32"),
            ("10.0.10.1", None, None),
            (None, "24", None),
            ("not-an-ip", "24", None),
        ],
    )
    def test_derives_network(self, ip, prefix, expected):
        assert derive_cidr(ip, prefix) == expected


class TestSSHCollection:
    @pytest.fixture()
    def result(self):
        return build_device_result(
            "cisco_ios",
            "10.0.10.1",
            {
                "version": SHOW_VERSION,
                "interfaces": SHOW_IP_INT_BRIEF,
                "cdp": SHOW_CDP_DETAIL,
            },
        )

    def test_identifies_the_polled_device(self, result):
        device = result.assets[0]
        assert device.source_ref == "R1"
        assert device.type == "network_device"
        assert device.vendor == "Cisco"
        assert device.model == "7206VXR"
        assert device.os_version == "15.2(4)S5"
        assert device.serial_number == "4279256517"

    def test_extracts_every_interface(self, result):
        names = {interface.name for interface in result.interfaces}
        assert names == {
            "FastEthernet0/0", "FastEthernet0/1", "Serial1/0", "Loopback0"
        }

    def test_unassigned_interface_has_no_address(self, result):
        serial = next(i for i in result.interfaces if i.name == "Serial1/0")
        assert serial.ip_address is None

    def test_discovers_neighbours_as_links(self, result):
        pairs = {
            (link.source_ref, link.target_ref, link.source_interface)
            for link in result.links
        }
        assert ("R1", "R2", "FastEthernet0/0") in pairs
        assert ("R1", "SW1", "FastEthernet0/1") in pairs

    def test_neighbour_fqdn_is_normalized(self, result):
        """R2.corp.example.com must not become a separate node from R2."""
        assert all(link.target_ref in {"R2", "SW1"} for link in result.links)

    def test_neighbours_become_placeholder_assets(self, result):
        placeholders = [a for a in result.assets if "discovered" in a.tags]
        assert {a.source_ref for a in placeholders} == {"R2", "SW1"}

    def test_empty_output_yields_only_the_device_itself(self):
        result = build_device_result("cisco_ios", "10.0.0.9", {})
        assert len(result.assets) == 1
        assert result.interfaces == []
        assert result.links == []

    def test_garbage_output_does_not_raise(self):
        result = build_device_result(
            "cisco_ios", "10.0.0.9",
            {"version": "%%%", "interfaces": "\x00\x01", "cdp": "???"},
        )
        assert result.assets  # degrades to the fallback hostname


# --------------------------------------------------------------------------
# SNMP
# --------------------------------------------------------------------------

class TestSNMP:
    @pytest.mark.parametrize(
        "oid,vendor",
        [
            ("1.3.6.1.4.1.9.1.222", "Cisco"),
            ("1.3.6.1.4.1.2636.1.1.1", "Juniper"),
            ("1.3.6.1.4.1.12356.101.1", "Fortinet"),
            ("1.3.6.1.4.1.99999.1", None),
            ("", None),
            (None, None),
        ],
    )
    def test_vendor_from_enterprise_oid(self, oid, vendor):
        assert vendor_from_sys_object_id(oid) == vendor

    @pytest.mark.parametrize(
        "descr,expected",
        [
            ("Cisco IOS Software, C2960 Software", "network_device"),
            ("Juniper Networks, Inc. srx240", "network_device"),
            ("Linux fileserver 5.15.0", "server"),
            ("Hardware: Intel64 ... Windows Server 2019", "server"),
        ],
    )
    def test_classifies_from_self_description(self, descr, expected):
        assert classify_from_sys_descr(descr) == expected

    def test_builds_asset_with_interfaces_and_neighbours(self):
        result = build_snmp_result(
            "10.0.30.1",
            {
                "sys_name": "DIST-SW-01.corp.local",
                "sys_descr": "Cisco IOS Software, C3560 Software",
                "sys_object_id": "1.3.6.1.4.1.9.1.222",
                "sys_location": "Riyadh DC1",
            },
            {
                "1": {
                    "name": "GigabitEthernet0/1",
                    "ip_address": "10.0.30.1",
                    "subnet_cidr": "10.0.30.0/24",
                    "status": "up",
                    "speed": "1000000000",
                },
                "2": {"name": "GigabitEthernet0/2", "status": "down"},
            },
            [{"sys_name": "CORE-RTR-01", "port_id": "Gi0/0/1"}],
        )

        device = result.assets[0]
        assert device.source_ref == "DIST-SW-01"
        assert device.vendor == "Cisco"
        assert device.location == "Riyadh DC1"
        assert device.type == "network_device"

        assert len(result.interfaces) == 2
        uplink = result.interfaces[0]
        assert uplink.speed == "1000 Mbps"

        assert len(result.links) == 1
        assert result.links[0].target_ref == "CORE-RTR-01"
        assert result.links[0].discovery_protocol == "LLDP"

    def test_self_reference_is_not_linked(self):
        """A device that lists itself as its own neighbour must be ignored."""
        result = build_snmp_result(
            "10.0.0.1",
            {"sys_name": "SW1", "sys_descr": "Cisco IOS"},
            {},
            [{"sys_name": "SW1", "port_id": "Gi0/1"}],
        )
        assert result.links == []


# --------------------------------------------------------------------------
# syslog
# --------------------------------------------------------------------------

class TestSyslogParsing:
    def test_decodes_priority_into_facility_and_severity(self):
        assert decode_priority(34) == ("auth", "critical")
        assert decode_priority(13) == ("user", "notice")

    def test_parses_rfc3164(self):
        event = parse_syslog_line(
            "<34>Oct 11 22:14:15 core-sw-01 %LINK-3-UPDOWN: Interface Gi0/1, changed state to down",
            "10.0.10.1",
        )
        assert event.hostname == "core-sw-01"
        assert event.severity == "critical"
        assert event.facility == "auth"
        assert "changed state to down" in event.message
        assert event.source_ip == "10.0.10.1"

    def test_parses_rfc5424_with_structured_data(self):
        event = parse_syslog_line(
            '<165>1 2026-08-21T10:15:30.003Z fw-01 sshd 1234 ID47 '
            '[exampleSDID@32473 iut="3"] Failed password for root',
            "10.0.40.1",
        )
        assert event.hostname == "fw-01"
        assert event.app_name == "sshd"
        assert event.message == "Failed password for root"
        assert event.severity == "notice"

    def test_parses_rfc5424_without_structured_data(self):
        event = parse_syslog_line("<13>1 2026-08-21T10:15:30Z host app - - - hello")
        assert event.hostname == "host"
        assert "hello" in event.message

    def test_unparseable_line_is_kept_not_dropped(self):
        """An unknown format must never mean a silently lost log."""
        event = parse_syslog_line("this is not syslog at all", "10.0.0.5")
        assert event.message == "this is not syslog at all"
        assert event.source_ip == "10.0.0.5"

    def test_empty_line_produces_empty_message(self):
        assert parse_syslog_line("   ").message == ""

    def test_senders_become_assets(self):
        events = [
            parse_syslog_line("<34>Oct 11 22:14:15 sw-a msg one", "10.0.0.1"),
            parse_syslog_line("<34>Oct 11 22:14:16 sw-a msg two", "10.0.0.1"),
            parse_syslog_line("<34>Oct 11 22:14:17 sw-b msg three", "10.0.0.2"),
        ]
        result = events_to_result(events)
        assert {a.source_ref for a in result.assets} == {"SW-A", "SW-B"}
        assert len(result.events) == 3


# --------------------------------------------------------------------------
# agent
# --------------------------------------------------------------------------

class TestAgentIngestion:
    @pytest.fixture()
    def payload(self):
        return {
            "agent_id": "agent-001",
            "hostname": "app-server-01.corp.local",
            "agent_version": "1.0.0",
            "asset_type": "server",
            "criticality": "high",
            "environment": "production",
            "system": {"os_name": "Linux", "os_version": "Ubuntu 24.04", "vendor": "Dell"},
            "network": {
                "primary_mac": "aa:bb:cc:dd:ee:ff",
                "interfaces": [
                    {"name": "lo", "ip_address": "127.0.0.1"},
                    {"name": "eth0", "ip_address": "10.0.50.20", "subnet_cidr": "10.0.50.0/24"},
                ],
            },
            "listening_ports": [
                {"port": 22, "address": "0.0.0.0"},
                {"port": 23, "address": "0.0.0.0"},
                {"port": 3306, "address": "0.0.0.0"},
                {"port": 6379, "address": "127.0.0.1"},
                {"port": 8080, "address": "0.0.0.0"},
            ],
        }

    def test_creates_asset_with_routable_address(self, payload):
        result = normalize_agent_payload(payload)
        asset = result.assets[0]
        assert asset.source_ref == "APP-SERVER-01"
        assert asset.ip_address == "10.0.50.20"  # not the loopback
        assert asset.criticality == "high"
        assert asset.vendor == "Dell"

    def test_flags_only_noteworthy_exposed_ports(self, payload):
        result = normalize_agent_payload(payload)
        ports = {finding.port for finding in result.vulnerabilities}
        assert 23 in ports      # telnet, critical
        assert 3306 in ports    # database exposed
        assert 22 not in ports  # ssh is expected, not a finding
        assert 8080 not in ports

    def test_loopback_bound_service_is_not_exposure(self, payload):
        """Redis on 127.0.0.1 is not reachable from the network."""
        result = normalize_agent_payload(payload)
        assert 6379 not in {finding.port for finding in result.vulnerabilities}

    def test_telnet_is_rated_critical(self, payload):
        result = normalize_agent_payload(payload)
        telnet = next(f for f in result.vulnerabilities if f.port == 23)
        assert telnet.severity == "critical"
        assert telnet.cvss_score >= 9.0

    def test_report_without_identity_is_rejected(self):
        result = normalize_agent_payload({"hostname": "", "agent_id": ""})
        assert result.assets == []
        assert result.errors

    def test_missing_sections_degrade_gracefully(self):
        result = normalize_agent_payload({"agent_id": "a1", "hostname": "host-1"})
        assert result.assets[0].source_ref == "HOST-1"
        assert result.interfaces == []


# --------------------------------------------------------------------------
# nmap
# --------------------------------------------------------------------------

NMAP_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
  <host>
    <status state="up"/>
    <address addr="10.0.60.11" addrtype="ipv4"/>
    <address addr="00:11:22:33:44:55" addrtype="mac" vendor="VMware"/>
    <hostnames><hostname name="db-01.corp.local"/></hostnames>
    <ports>
      <port protocol="tcp" portid="3306">
        <state state="open"/>
        <service name="mysql" product="MySQL" version="8.0.35"/>
      </port>
      <port protocol="tcp" portid="22">
        <state state="open"/><service name="ssh"/>
      </port>
      <port protocol="tcp" portid="8080">
        <state state="closed"/><service name="http"/>
      </port>
    </ports>
    <os><osmatch name="Linux 5.4"/></os>
  </host>
  <host>
    <status state="down"/>
    <address addr="10.0.60.12" addrtype="ipv4"/>
  </host>
</nmaprun>
"""


class TestNmapIngestion:
    def test_skips_hosts_that_are_down(self):
        result = parse_nmap_xml(NMAP_XML)
        assert len(result.assets) == 1

    def test_extracts_identity_and_classification(self):
        result = parse_nmap_xml(NMAP_XML)
        asset = result.assets[0]
        assert asset.source_ref == "DB-01"
        assert asset.ip_address == "10.0.60.11"
        assert asset.mac_address == "00:11:22:33:44:55"
        assert asset.vendor == "VMware"
        assert asset.type == "server"  # OS match wins over service heuristics

    def test_reports_exposed_database_with_banner(self):
        result = parse_nmap_xml(NMAP_XML)
        finding = next(f for f in result.vulnerabilities if f.port == 3306)
        assert "MySQL 8.0.35" in (finding.description or "")

    def test_closed_ports_are_ignored(self):
        result = parse_nmap_xml(NMAP_XML)
        assert 8080 not in {f.port for f in result.vulnerabilities}

    def test_invalid_xml_is_an_error_not_a_crash(self):
        result = parse_nmap_xml("<not-xml")
        assert result.errors
        assert result.assets == []


# --------------------------------------------------------------------------
# credential handling
# --------------------------------------------------------------------------

class TestSecrets:
    def test_round_trip(self):
        assert decrypt_secret(encrypt_secret("Sup3rSecret!")) == "Sup3rSecret!"

    def test_ciphertext_does_not_contain_plaintext(self):
        token = encrypt_secret("Sup3rSecret!")
        assert "Sup3rSecret!" not in token
        assert token.startswith("enc:v1:")

    def test_encryption_is_not_deterministic(self):
        """Identical passwords must not produce identical ciphertext."""
        assert encrypt_secret("same") != encrypt_secret("same")

    def test_double_encryption_is_a_no_op(self):
        once = encrypt_secret("value")
        assert encrypt_secret(once) == once

    def test_empty_values_pass_through(self):
        assert encrypt_secret(None) is None
        assert encrypt_secret("") == ""

    def test_only_named_fields_are_encrypted(self):
        config = {"username": "admin", "password": "secret", "port": 22}
        stored = encrypt_config(config, {"password"})
        assert stored["username"] == "admin"
        assert stored["port"] == 22
        assert stored["password"].startswith("enc:v1:")
        assert decrypt_config(stored, {"password"})["password"] == "secret"

    def test_redaction_hides_secrets_but_keeps_shape(self):
        redacted = redact_config({"username": "admin", "password": "secret"}, {"password"})
        assert redacted["username"] == "admin"
        assert redacted["password"] == "••••••••"

    def test_api_key_is_hashed_not_stored(self):
        key = generate_api_key()
        assert key.startswith("csos_")
        digest = hash_api_key(key)
        assert len(digest) == 64
        assert key not in digest
        assert hash_api_key(key) == digest  # stable


# --------------------------------------------------------------------------
# graph writer
# --------------------------------------------------------------------------

class RecordingClient:
    """Stands in for Neo4j, recording every query and returning plausible rows.

    Enough to assert the writer's correlation and precedence logic without a
    database, which is what those rules actually need testing for.
    """

    def __init__(self, existing: dict[str, int] | None = None):
        self.queries: list[tuple[str, dict]] = []
        #: source_ref -> confidence of the node already in the graph
        self.existing = existing or {}
        self._ids: dict[str, str] = {}

    def run(self, query: str, parameters: dict | None = None):
        parameters = parameters or {}
        self.queries.append((query, parameters))
        normalized = " ".join(query.split())

        if normalized.startswith("MATCH (a:Asset {source_ref: $source_ref}) RETURN a.id"):
            ref = parameters["source_ref"]
            if ref in self.existing:
                return [{"id": self._ids.setdefault(ref, f"id-{ref}"),
                         "confidence": self.existing[ref]}]
            return []

        if "MERGE (a:Asset {source_ref: $source_ref})" in normalized:
            ref = parameters["source_ref"]
            return [{"id": self._ids.setdefault(ref, f"id-{ref}")}]

        if "MERGE (i:NetworkInterface" in normalized:
            return [{"id": "iface-1"}]
        if "MERGE (v:Vulnerability" in normalized:
            return [{"id": "vuln-1"}]
        if "MERGE (source)-[rel:" in normalized:
            return [{"id": "rel-1"}]
        return []

    def queries_matching(self, fragment: str) -> list[tuple[str, dict]]:
        return [(q, p) for q, p in self.queries if fragment in " ".join(q.split())]


class TestNetworkGraphWriter:
    def _writer(self, client):
        from app.graph.network_writer import NetworkGraphWriter

        return NetworkGraphWriter(client=client)

    def test_writes_assets_interfaces_and_links(self):
        result = build_device_result(
            "cisco_ios", "10.0.10.1",
            {"version": SHOW_VERSION, "interfaces": SHOW_IP_INT_BRIEF, "cdp": SHOW_CDP_DETAIL},
        )
        client = RecordingClient()
        stats = self._writer(client).write(result)

        assert stats["assets"] == 3      # R1 plus two neighbours
        assert stats["interfaces"] == 4
        assert stats["links"] == 2

    def test_assets_merge_on_source_ref(self):
        """Correlation key must be source_ref, or duplicates are guaranteed."""
        client = RecordingClient()
        result = CollectionResult(connector_key="snmp")
        result.assets.append(CollectedAsset(source_ref="R1", name="R1"))
        self._writer(client).upsert_assets(result)

        merges = client.queries_matching("MERGE (a:Asset {source_ref: $source_ref})")
        assert merges
        assert merges[0][1]["source_ref"] == "R1"

    def test_direct_poll_outranks_hearsay(self):
        """An SSH poll must be able to correct a CDP-discovered placeholder."""
        client = RecordingClient(existing={"R2": 5})
        result = CollectionResult(connector_key="ssh_network")
        result.assets.append(
            CollectedAsset(source_ref="R2", name="R2", vendor="Cisco", model="ISR4331")
        )
        self._writer(client).upsert_assets(result)

        overwrites = client.queries_matching("SET a += $props")
        assert overwrites, "الموصّل الأقوى لم يُحدِّث الحقول المرجعية"
        assert overwrites[0][1]["props"]["model"] == "ISR4331"

    def test_hearsay_does_not_overwrite_a_direct_poll(self):
        """A neighbour's guess must not clobber what SSH established."""
        client = RecordingClient(existing={"R2": 35})
        result = CollectionResult(connector_key="syslog")
        neighbour = CollectedAsset(
            source_ref="R2", name="R2", vendor="Unknown", tags=["discovered"]
        )
        result.assets.append(neighbour)
        self._writer(client).upsert_assets(result)

        assert not client.queries_matching("SET a += $props")

    def test_self_link_is_skipped(self):
        client = RecordingClient()
        result = CollectionResult(connector_key="ssh_network")
        result.links.append(CollectedLink(source_ref="R1", target_ref="R1"))
        assert self._writer(client).upsert_links(result) == 0

    def test_unknown_relationship_type_is_refused(self):
        """Relationship type is interpolated, so the allow-list is a real control."""
        client = RecordingClient()
        result = CollectionResult(connector_key="ssh_network")
        link = CollectedLink(source_ref="A", target_ref="B")
        link.link_type = "DROP DATABASE"  # type: ignore[assignment]
        result.links.append(link)

        assert self._writer(client).upsert_links(result) == 0
        assert result.errors
        assert not client.queries_matching("MERGE (source)-[rel:")

    def test_vulnerabilities_merge_on_identity_not_a_new_id(self):
        """A repeated scan must update findings, not duplicate them."""
        result = parse_nmap_xml(NMAP_XML)
        client = RecordingClient()
        self._writer(client).upsert_vulnerabilities(result)

        merges = client.queries_matching("MERGE (v:Vulnerability {identity: $identity})")
        assert merges
        assert merges[0][1]["identity"]

    def test_vendor_finding_identity_is_scoped_to_connector(self):
        result = CollectionResult(connector_key="edr_xdr_api")
        result.vulnerabilities.append(CollectedVulnerability(
            title="Vendor alert", vendor_finding_id="alert-42"
        ))
        client = RecordingClient()
        self._writer(client).upsert_vulnerabilities(result)

        merges = client.queries_matching("MERGE (v:Vulnerability {identity: $identity})")
        assert merges[0][1]["identity"] == "edr_xdr_api:alert-42"

    def test_events_are_written_and_trimmed(self):
        events = [parse_syslog_line(f"<34>Oct 11 22:14:{i:02d} sw-a message {i}", "10.0.0.1")
                  for i in range(10)]
        client = RecordingClient()
        written = self._writer(client).write_events(events_to_result(events))

        assert written == 10
        assert client.queries_matching("DETACH DELETE e"), "لم تُطبَّق نافذة الاحتفاظ"

    def test_writing_nothing_is_safe(self):
        client = RecordingClient()
        stats = self._writer(client).write(CollectionResult(connector_key="snmp"))
        assert stats == {
            "assets": 0, "interfaces": 0, "links": 0,
            "vulnerabilities": 0, "events": 0,
        }
