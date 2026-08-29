"""Cross-platform parser checks for the standalone CSOS endpoint reporter."""
from __future__ import annotations

import pathlib
import sys

import pytest

AGENT_DIR = pathlib.Path(__file__).resolve().parents[2] / "agent"
sys.path.insert(0, str(AGENT_DIR))

from csos_agent import build_report, collect_network, collect_system, parse_listening_ports, split_host_port  # noqa: E402


@pytest.mark.parametrize("value,expected", [
    ("0.0.0.0:8443", ("0.0.0.0", 8443)),
    ("127.0.0.1.631", ("127.0.0.1", 631)),
    ("[::]:443", ("::", 443)),
    ("*:22", ("*", 22)),
])
def test_listener_endpoint_formats(value, expected):
    assert split_host_port(value) == expected


@pytest.mark.parametrize("value", ["0", "*.*", "tcp", "", "0.0.0.0:0", "1.2.3.4:65536"])
def test_non_endpoints_are_ignored(value):
    assert split_host_port(value) is None


def test_linux_listener_output_is_deduplicated():
    output = """State Recv-Q Send-Q Local Address:Port Peer Address:Port
LISTEN 0 128 0.0.0.0:8443 0.0.0.0:*
LISTEN 0 128 127.0.0.1:5432 0.0.0.0:*
LISTEN 0 128 0.0.0.0:8443 0.0.0.0:*
ESTAB 0 0 172.16.60.24:52000 198.51.100.10:443
"""
    listeners = parse_listening_ports(output, "ss")
    assert {(item["address"], item["port"]) for item in listeners} == {("0.0.0.0", 8443), ("127.0.0.1", 5432)}


def test_macos_lsof_preserves_process_name():
    output = """COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
websvc 901 svc 7u IPv4 0x1 0t0 TCP *:9443 (LISTEN)
"""
    assert parse_listening_ports(output, "lsof") == [{"port": 9443, "address": "*", "protocol": "tcp", "process": "websvc"}]


def test_live_report_has_stable_required_shape():
    class Options:
        asset_type = "server"
        criticality = "high"
        environment = "test"
        owner = "Platform Operations"
        no_packages = True

    first = build_report(Options())
    second = build_report(Options())
    assert first["agent_id"] == second["agent_id"]
    assert all(first[field] for field in ("agent_id", "hostname", "agent_version", "system", "network"))


def test_live_collectors_always_return_core_inventory():
    assert collect_system()["os_name"]
    assert any(item.get("ip_address") for item in collect_network()["interfaces"])
