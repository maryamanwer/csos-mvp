#!/usr/bin/env python3
"""CSOS endpoint agent.

Collects local inventory and reports it to the platform. Deliberately built on
the Python standard library alone — no pip install on a production server, no
dependency to patch, and it runs on any host with Python 3.8 or later. That
matters most on the machines you least want to touch.

Read-only. The agent never changes anything on the host it runs on.

    python3 csos_agent.py --server https://csos.internal --api-key csos_xxx
    python3 csos_agent.py --server ... --api-key ... --daemon --interval 3600
    python3 csos_agent.py --dry-run          # print the report, send nothing
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

AGENT_VERSION = "1.0.0"
DEFAULT_INTERVAL = 3600
STATE_FILENAME = ".csos-agent-id"


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------

def stable_agent_id() -> str:
    """A per-host identifier that survives restarts.

    Stored beside the agent so the same machine is not re-registered as a new
    asset on every run. Falls back to a MAC-derived UUID when the filesystem is
    read-only.
    """
    state_path = os.path.join(
        os.environ.get("CSOS_AGENT_STATE_DIR", os.path.expanduser("~")),
        STATE_FILENAME,
    )
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as handle:
                existing = handle.read().strip()
                if existing:
                    return existing
    except OSError:
        pass

    agent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{socket.getfqdn()}|{uuid.getnode()}"))
    try:
        with open(state_path, "w", encoding="utf-8") as handle:
            handle.write(agent_id)
    except OSError:
        pass
    return agent_id


def _run(command: list[str], timeout: int = 10) -> str:
    """Run a helper command, returning '' rather than raising on any failure."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return completed.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


# --------------------------------------------------------------------------
# collection
# --------------------------------------------------------------------------

def collect_system() -> dict:
    system = {
        "os_name": platform.system(),
        "os_version": platform.release(),
        "vendor": None,
        "model": None,
        "serial_number": None,
    }

    if platform.system() == "Linux":
        for key, path in (
            ("vendor", "/sys/class/dmi/id/sys_vendor"),
            ("model", "/sys/class/dmi/id/product_name"),
            ("serial_number", "/sys/class/dmi/id/product_serial"),
        ):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    value = handle.read().strip()
                    if value and value.lower() not in ("none", "to be filled by o.e.m."):
                        system[key] = value
            except OSError:
                pass
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("PRETTY_NAME="):
                        system["os_version"] = line.split("=", 1)[1].strip().strip('"')
                        break
        except OSError:
            pass

    elif platform.system() == "Darwin":
        output = _run(["system_profiler", "SPHardwareDataType"])
        system["vendor"] = "Apple"
        for pattern, key in (
            (r"Model Identifier:\s*(.+)", "model"),
            (r"Serial Number \(system\):\s*(.+)", "serial_number"),
        ):
            match = re.search(pattern, output)
            if match:
                system[key] = match.group(1).strip()
        system["os_version"] = platform.mac_ver()[0] or system["os_version"]

    elif platform.system() == "Windows":
        output = _run(
            ["wmic", "csproduct", "get", "Vendor,Name,IdentifyingNumber", "/format:list"]
        )
        for pattern, key in (
            (r"Vendor=(.+)", "vendor"),
            (r"Name=(.+)", "model"),
            (r"IdentifyingNumber=(.+)", "serial_number"),
        ):
            match = re.search(pattern, output)
            if match:
                system[key] = match.group(1).strip()

    return system


def collect_network() -> dict:
    """Enumerate interfaces without third-party libraries.

    ``socket`` alone cannot list interfaces, so this parses the platform's own
    tooling and always falls back to at least the primary address.
    """
    interfaces: list[dict] = []
    primary_mac = None

    node = uuid.getnode()
    # getnode() invents a random multicast address when it cannot read a real
    # one; bit 41 set is the documented marker for that.
    if not (node >> 40) & 0x01:
        primary_mac = ":".join(
            f"{(node >> element) & 0xFF:02x}" for element in range(40, -8, -8)
        )

    system = platform.system()
    if system == "Linux":
        output = _run(["ip", "-o", "addr", "show"])
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 4 or parts[2] not in ("inet", "inet6"):
                continue
            name = parts[1]
            address = parts[3]
            ip_address, _, prefix = address.partition("/")
            if parts[2] == "inet6":
                continue
            interfaces.append(
                {
                    "name": name,
                    "ip_address": ip_address,
                    "subnet_cidr": _network_of(ip_address, prefix),
                    "status": "up",
                }
            )
    elif system in ("Darwin", "FreeBSD"):
        output = _run(["ifconfig"])
        current = None
        for line in output.splitlines():
            if line and not line[0].isspace():
                current = line.split(":", 1)[0]
            elif current and "inet " in line:
                parts = line.split()
                try:
                    ip_address = parts[parts.index("inet") + 1]
                except (ValueError, IndexError):
                    continue
                interfaces.append(
                    {"name": current, "ip_address": ip_address, "status": "up"}
                )
    elif system == "Windows":
        output = _run(["ipconfig"])
        current = "ethernet"
        for line in output.splitlines():
            if line and not line.startswith(" "):
                current = line.strip().rstrip(":") or current
            elif "IPv4 Address" in line and ":" in line:
                interfaces.append(
                    {
                        "name": current[:60],
                        "ip_address": line.split(":", 1)[1].strip().rstrip("(Preferred)"),
                        "status": "up",
                    }
                )

    if not interfaces:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            interfaces.append(
                {"name": "primary", "ip_address": probe.getsockname()[0], "status": "up"}
            )
            probe.close()
        except OSError:
            try:
                interfaces.append(
                    {
                        "name": "primary",
                        "ip_address": socket.gethostbyname(socket.gethostname()),
                        "status": "up",
                    }
                )
            except OSError:
                pass

    return {"primary_mac": primary_mac, "interfaces": interfaces}


def _network_of(ip_address: str, prefix: str) -> str | None:
    try:
        import ipaddress

        return str(ipaddress.ip_network(f"{ip_address}/{int(prefix)}", strict=False))
    except (ValueError, TypeError):
        return None


def split_host_port(token: str) -> tuple[str, int] | None:
    """Split an address token into host and port across platform formats.

    The separator is not the same everywhere, and getting this wrong means the
    agent silently reports zero listening ports:

        Linux  ss/netstat   127.0.0.1:631     colon
        macOS  netstat -an  127.0.0.1.631     dot
        macOS  lsof         127.0.0.1:631     colon
        IPv6                [::1]:631 / ::1.631

    Returns ``None`` for anything that is not a real host/port pair — including
    bare numbers such as the Recv-Q column, which would otherwise parse as
    port 0 on a dot split.
    """
    token = token.strip()
    for separator in (":", "."):
        host, found, port_text = token.rpartition(separator)
        if not found or not host or not port_text.isdigit():
            continue
        port = int(port_text)
        if not 1 <= port <= 65535:
            continue
        return host.strip("[]") or "0.0.0.0", port
    return None


def parse_listening_ports(output: str, source: str) -> list[dict]:
    """Parse listener output from lsof, ss, or netstat into canonical rows."""
    ports: list[dict] = []
    seen: set[tuple[str, int]] = set()

    for line in output.splitlines():
        upper = line.upper()
        if "LISTEN" not in upper:
            continue

        process = None
        candidates: list[str]
        if source == "lsof":
            parts = line.split()
            if len(parts) < 2:
                continue
            process = parts[0]
            # The NAME column is the token immediately before "(LISTEN)".
            candidates = [
                parts[index - 1]
                for index, token in enumerate(parts)
                if token.upper().startswith("(LISTEN") and index > 0
            ]
        else:
            candidates = line.split()

        for token in candidates:
            parsed = split_host_port(token)
            if parsed is None:
                continue
            address, port = parsed
            if (address, port) in seen:
                break
            seen.add((address, port))
            entry = {"port": port, "address": address, "protocol": "tcp"}
            if process:
                entry["process"] = process
            ports.append(entry)
            break  # first valid pair on the line is the local address

    return ports


def collect_listening_ports() -> list[dict]:
    """Ports the host accepts connections on — its actual attack surface."""
    system = platform.system()

    if system == "Darwin":
        # lsof is the reliable option on macOS and names the process too;
        # netstat there has no -p flag and uses a dot before the port.
        output = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], timeout=20)
        if output.strip():
            return parse_listening_ports(output, "lsof")
        return parse_listening_ports(_run(["netstat", "-an", "-p", "tcp"]), "netstat")

    if system == "Linux":
        output = _run(["ss", "-tlnp"])
        if output.strip():
            return parse_listening_ports(output, "ss")
        output = _run(["netstat", "-tlnp"]) or _run(["netstat", "-an"])
        return parse_listening_ports(output, "netstat")

    if system == "Windows":
        return parse_listening_ports(_run(["netstat", "-ano", "-p", "TCP"]), "netstat")

    return []


def collect_packages(limit: int = 500) -> list[str]:
    """Installed package names, for later vulnerability correlation."""
    system = platform.system()
    output = ""
    if system == "Linux":
        output = _run(["dpkg-query", "-W", "-f=${Package} ${Version}\n"], timeout=25)
        if not output:
            output = _run(["rpm", "-qa"], timeout=25)
    elif system == "Darwin":
        output = _run(["brew", "list", "--versions"], timeout=25)
    return [line.strip() for line in output.splitlines() if line.strip()][:limit]


def build_report(args) -> dict:
    return {
        "agent_id": stable_agent_id(),
        "hostname": socket.gethostname(),
        "agent_version": AGENT_VERSION,
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "asset_type": args.asset_type,
        "criticality": args.criticality,
        "environment": args.environment,
        "owner": args.owner,
        "system": collect_system(),
        "network": collect_network(),
        "listening_ports": collect_listening_ports(),
        "packages": [] if args.no_packages else collect_packages(),
    }


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def send_report(report: dict, server: str, api_key: str, *, insecure: bool = False,
                timeout: int = 30) -> tuple[bool, str]:
    url = server.rstrip("/") + "/api/v1/ingest/agent"
    body = json.dumps(report).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": f"csos-agent/{AGENT_VERSION}",
        },
        method="POST",
    )

    context = None
    if url.startswith("https://"):
        context = ssl.create_default_context()
        if insecure:
            # Present because an air-gapped deployment often uses an internal CA
            # that is not in the host trust store. Never enable it by default.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return True, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {detail}"
    except (urllib.error.URLError, OSError, ssl.SSLError) as exc:
        return False, f"Unable to reach the server: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="CSOS endpoint inventory agent")
    parser.add_argument("--server", help="Platform URL, for example https://csos.internal")
    parser.add_argument("--api-key", dest="api_key", help="Ingestion API key issued by CSOS")
    parser.add_argument("--environment", default="production")
    parser.add_argument(
        "--criticality", default="medium",
        choices=["low", "medium", "high", "critical"],
    )
    parser.add_argument(
        "--asset-type", dest="asset_type", default="server",
        choices=["server", "application", "network_device", "endpoint", "workstation", "database", "cloud_resource"],
    )
    parser.add_argument("--owner", default=None)
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--dry-run", action="store_true", help="Print the report without sending it")
    parser.add_argument("--no-packages", action="store_true", help="Skip package inventory")
    parser.add_argument(
        "--insecure", action="store_true",
        help="Disable TLS certificate verification (internal testing only)",
    )
    args = parser.parse_args()

    # Environment variables let a service unit hold the key out of the process
    # table, where --api-key would be visible to every user via ps.
    args.server = args.server or os.environ.get("CSOS_SERVER")
    args.api_key = args.api_key or os.environ.get("CSOS_API_KEY")

    if args.dry_run:
        print(json.dumps(build_report(args), indent=2, ensure_ascii=False))
        return 0

    if not args.server or not args.api_key:
        parser.error("--server and --api-key are required (or use CSOS_SERVER and CSOS_API_KEY)")

    while True:
        report = build_report(args)
        ok, message = send_report(
            report, args.server, args.api_key, insecure=args.insecure
        )
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if ok:
            print(
                f"[{stamp}] Report sent — "
                f"{len(report['network']['interfaces'])} interfaces, "
                f"{len(report['listening_ports'])} listening ports"
            )
        else:
            print(f"[{stamp}] Send failed: {message}", file=sys.stderr)

        if not args.daemon:
            return 0 if ok else 1
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    sys.exit(main())
