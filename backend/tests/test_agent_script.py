"""Tests for the standalone endpoint agent.

The agent ships as a single stdlib-only file and runs on machines nobody is
watching, so its parsers have to be right on every platform without a chance
to debug in place. Address formats differ between Linux, macOS and Windows —
and a mismatch there does not raise, it silently reports zero listening ports,
which reads as "this host is clean" when it means "the parser failed".
"""
from __future__ import annotations

import pathlib
import sys

import pytest

AGENT_DIR = pathlib.Path(__file__).resolve().parents[2] / "agent"
sys.path.insert(0, str(AGENT_DIR))

from csos_agent import (  # noqa: E402
    build_report,
    collect_network,
    collect_system,
    parse_listening_ports,
    split_host_port,
)


# Captured from real systems — the separator differences below are the whole
# reason this module exists.

MACOS_NETSTAT = """Active Internet connections (including servers)
Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)
tcp4       0      0  127.0.0.1.631          *.*                    LISTEN
tcp6       0      0  *.22                   *.*                    LISTEN
tcp4       0      0  192.168.3.38.5000      *.*                    LISTEN
tcp4       0      0  192.168.3.38.49232     17.253.55.201.443      ESTABLISHED
"""

MACOS_LSOF = """COMMAND     PID   USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
launchd       1   root   28u  IPv6 0x1234          0t0  TCP *:22 (LISTEN)
rapportd    412 wejdan    5u  IPv4 0x5678          0t0  TCP 127.0.0.1:50000 (LISTEN)
cupsd        98   root    7u  IPv6 0x9abc          0t0  TCP [::1]:631 (LISTEN)
Google      771 wejdan   40u  IPv4 0xdef0          0t0  TCP 192.168.3.38:49232->17.253.55.201:443 (ESTABLISHED)
"""

LINUX_SS = """State   Recv-Q  Send-Q   Local Address:Port    Peer Address:Port  Process
LISTEN  0       128            0.0.0.0:22           0.0.0.0:*          users:(("sshd",pid=1,fd=3))
LISTEN  0       128          127.0.0.1:5432         0.0.0.0:*
LISTEN  0       128               [::]:80              [::]:*
"""

WINDOWS_NETSTAT = """  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:445            0.0.0.0:0              LISTENING       4
  TCP    127.0.0.1:3389         0.0.0.0:0              LISTENING       892
  TCP    192.168.1.5:52001      93.184.216.34:443      ESTABLISHED     4120
"""


class TestSplitHostPort:
    @pytest.mark.parametrize(
        "token,expected",
        [
            ("127.0.0.1:631", ("127.0.0.1", 631)),      # Linux / lsof
            ("127.0.0.1.631", ("127.0.0.1", 631)),      # macOS netstat
            ("[::1]:631", ("::1", 631)),                # IPv6 bracketed
            ("*:22", ("*", 22)),
            ("*.22", ("*", 22)),
            ("0.0.0.0:22", ("0.0.0.0", 22)),
        ],
    )
    def test_recognized_formats(self, token, expected):
        assert split_host_port(token) == expected

    @pytest.mark.parametrize(
        "token",
        [
            "0",          # a Recv-Q column, not an address
            "128",
            "*.*",        # wildcard foreign address
            "abc",
            "",
            "0.0.0.0:0",  # port 0 is not a listener
            "1.2.3.4:70000",
            "tcp4",
        ],
    )
    def test_rejects_non_addresses(self, token):
        """A bare column value must not parse as port 0 on a dot split."""
        assert split_host_port(token) is None


class TestParseListeningPorts:
    def test_macos_netstat_dot_separator(self):
        """The bug this guards: macOS puts a dot before the port, not a colon."""
        ports = parse_listening_ports(MACOS_NETSTAT, "netstat")
        assert {entry["port"] for entry in ports} == {631, 22, 5000}

    def test_macos_lsof_includes_process_name(self):
        ports = parse_listening_ports(MACOS_LSOF, "lsof")
        by_port = {entry["port"]: entry for entry in ports}
        assert by_port[22]["process"] == "launchd"
        assert by_port[50000]["address"] == "127.0.0.1"
        assert by_port[631]["address"] == "::1"

    def test_linux_ss(self):
        ports = parse_listening_ports(LINUX_SS, "ss")
        assert {entry["port"] for entry in ports} == {22, 5432, 80}

    def test_windows_netstat(self):
        ports = parse_listening_ports(WINDOWS_NETSTAT, "netstat")
        assert {entry["port"] for entry in ports} == {445, 3389}

    @pytest.mark.parametrize(
        "output,source",
        [
            (MACOS_NETSTAT, "netstat"),
            (MACOS_LSOF, "lsof"),
            (LINUX_SS, "ss"),
            (WINDOWS_NETSTAT, "netstat"),
        ],
    )
    def test_established_connections_are_never_listeners(self, output, source):
        """An outbound connection is not an exposed port."""
        ports = parse_listening_ports(output, source)
        assert 49232 not in {entry["port"] for entry in ports}
        assert 52001 not in {entry["port"] for entry in ports}

    def test_duplicates_collapse(self):
        doubled = LINUX_SS + LINUX_SS.split("\n", 1)[1]
        ports = parse_listening_ports(doubled, "ss")
        assert len(ports) == len({(e["address"], e["port"]) for e in ports})

    def test_empty_input(self):
        assert parse_listening_ports("", "ss") == []

    def test_garbage_input_does_not_raise(self):
        assert parse_listening_ports("\x00\x01 LISTEN \xff", "netstat") == []


class TestLocalCollection:
    """Runs against the host executing the tests — no fixtures, real output."""

    def test_system_facts_are_populated(self):
        system = collect_system()
        assert system["os_name"]
        assert system["os_version"]

    def test_network_always_yields_an_address(self):
        """Interface enumeration must degrade to at least the primary address."""
        network = collect_network()
        assert network["interfaces"]
        assert any(entry.get("ip_address") for entry in network["interfaces"])

    def test_report_has_the_fields_the_api_requires(self):
        class Args:
            asset_type = "server"
            criticality = "medium"
            environment = "production"
            owner = None
            no_packages = True

        report = build_report(Args())
        for field in ("agent_id", "hostname", "agent_version", "system", "network"):
            assert field in report
        assert report["agent_id"]
        assert report["hostname"]

    def test_agent_id_is_stable_across_runs(self):
        """An unstable id would re-register the same host as a new asset."""
        class Args:
            asset_type = "server"
            criticality = "medium"
            environment = "production"
            owner = None
            no_packages = True

        assert build_report(Args())["agent_id"] == build_report(Args())["agent_id"]
