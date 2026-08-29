#!/usr/bin/env python3
"""CSOS read-only endpoint reporter (Python standard library only)."""
from __future__ import annotations

import argparse
import ipaddress
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

AGENT_VERSION = "2.0.0"
DEFAULT_INTERVAL = 3600
STATE_FILENAME = ".csos-endpoint-id"


def _command(arguments: list[str], timeout: int = 15) -> str:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def stable_agent_id() -> str:
    state_root = os.environ.get("CSOS_AGENT_STATE_DIR") or os.path.expanduser("~")
    state_file = os.path.join(state_root, STATE_FILENAME)
    try:
        with open(state_file, encoding="utf-8") as handle:
            saved = handle.read().strip()
            if saved:
                return saved
    except OSError:
        pass
    generated = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{socket.getfqdn()}:{uuid.getnode()}"))
    try:
        os.makedirs(state_root, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as handle:
            handle.write(generated)
    except OSError:
        pass
    return generated


def _read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            value = handle.read().strip()
        return value or None
    except OSError:
        return None


def collect_system() -> dict:
    os_name = platform.system()
    facts = {
        "os_name": os_name,
        "os_version": platform.release() or platform.version(),
        "vendor": None,
        "model": None,
        "serial_number": None,
    }
    if os_name == "Linux":
        facts.update({
            "vendor": _read_text("/sys/class/dmi/id/sys_vendor"),
            "model": _read_text("/sys/class/dmi/id/product_name"),
            "serial_number": _read_text("/sys/class/dmi/id/product_serial"),
        })
        release = _read_text("/etc/os-release") or ""
        match = re.search(r'(?m)^PRETTY_NAME="?([^"\n]+)', release)
        if match:
            facts["os_version"] = match.group(1)
    elif os_name == "Darwin":
        hardware = _command(["system_profiler", "SPHardwareDataType"])
        facts["vendor"] = "Apple"
        for field, pattern in {
            "model": r"Model Identifier:\s*(.+)",
            "serial_number": r"Serial Number \(system\):\s*(.+)",
        }.items():
            match = re.search(pattern, hardware)
            if match:
                facts[field] = match.group(1).strip()
        facts["os_version"] = platform.mac_ver()[0] or facts["os_version"]
    elif os_name == "Windows":
        hardware = _command(["wmic", "csproduct", "get", "Vendor,Name,IdentifyingNumber", "/format:list"])
        for field, pattern in {
            "vendor": r"(?m)^Vendor=(.+)",
            "model": r"(?m)^Name=(.+)",
            "serial_number": r"(?m)^IdentifyingNumber=(.+)",
        }.items():
            match = re.search(pattern, hardware)
            if match:
                facts[field] = match.group(1).strip()
    return facts


def _subnet(address: str, prefix: str | int) -> str | None:
    try:
        return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))
    except ValueError:
        return None


def _fallback_address() -> str | None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return probe.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None
    finally:
        probe.close()


def collect_network() -> dict:
    interfaces: list[dict] = []
    system = platform.system()
    if system == "Linux":
        for line in _command(["ip", "-o", "-4", "addr", "show"]).splitlines():
            columns = line.split()
            if len(columns) < 4 or columns[2] != "inet":
                continue
            address, _, prefix = columns[3].partition("/")
            interfaces.append({"name": columns[1], "ip_address": address, "subnet_cidr": _subnet(address, prefix), "status": "up"})
    elif system in {"Darwin", "FreeBSD"}:
        current = None
        for line in _command(["ifconfig"]).splitlines():
            if line and not line[0].isspace():
                current = line.split(":", 1)[0]
            elif current and re.search(r"\binet\s", line):
                address = line.split()[1]
                interfaces.append({"name": current, "ip_address": address, "status": "up"})
    elif system == "Windows":
        current = "ethernet"
        for line in _command(["ipconfig"]).splitlines():
            if line and not line[0].isspace():
                current = line.rstrip(":").strip() or current
            elif "IPv4 Address" in line and ":" in line:
                interfaces.append({"name": current[:60], "ip_address": line.rsplit(":", 1)[1].replace("(Preferred)", "").strip(), "status": "up"})
    if not interfaces:
        fallback = _fallback_address()
        if fallback:
            interfaces.append({"name": "primary", "ip_address": fallback, "status": "up"})

    node = uuid.getnode()
    mac = None
    if ((node >> 40) & 1) == 0:
        mac = ":".join(f"{(node >> shift) & 0xff:02x}" for shift in range(40, -1, -8))
    return {"primary_mac": mac, "interfaces": interfaces}


def split_host_port(token: str) -> tuple[str, int] | None:
    candidate = token.strip().strip(",")
    for separator in (":", "."):
        host, marker, port_text = candidate.rpartition(separator)
        if not marker or not host or not port_text.isdigit():
            continue
        port = int(port_text)
        if 1 <= port <= 65535:
            return host.strip("[]") or "0.0.0.0", port
    return None


def parse_listening_ports(output: str, source: str) -> list[dict]:
    discovered: dict[tuple[str, int], dict] = {}
    for line in output.splitlines():
        if "LISTEN" not in line.upper():
            continue
        columns = line.split()
        process = columns[0] if source == "lsof" and columns else None
        if source == "lsof":
            candidates = [columns[index - 1] for index, value in enumerate(columns) if index and value.upper().startswith("(LISTEN")]
        else:
            candidates = columns
        for candidate in candidates:
            endpoint = split_host_port(candidate)
            if endpoint is None:
                continue
            address, port = endpoint
            row = {"port": port, "address": address, "protocol": "tcp"}
            if process:
                row["process"] = process
            discovered[(address, port)] = row
            break
    return list(discovered.values())


def collect_listening_ports() -> list[dict]:
    system = platform.system()
    if system == "Linux":
        output = _command(["ss", "-tlnp"])
        return parse_listening_ports(output or _command(["netstat", "-tlnp"]), "ss" if output else "netstat")
    if system == "Darwin":
        output = _command(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
        return parse_listening_ports(output, "lsof") if output else parse_listening_ports(_command(["netstat", "-an", "-p", "tcp"]), "netstat")
    if system == "Windows":
        return parse_listening_ports(_command(["netstat", "-ano", "-p", "TCP"]), "netstat")
    return []


def collect_packages(limit: int = 500) -> list[str]:
    system = platform.system()
    if system == "Linux":
        output = _command(["dpkg-query", "-W", "-f=${Package} ${Version}\n"], 30) or _command(["rpm", "-qa"], 30)
    elif system == "Darwin":
        output = _command(["brew", "list", "--versions"], 30)
    else:
        output = ""
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


def send_report(report: dict, server: str, api_key: str, *, insecure: bool = False, timeout: int = 30) -> tuple[bool, str]:
    request = urllib.request.Request(
        server.rstrip("/") + "/api/v1/ingest/agent",
        data=json.dumps(report).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key, "User-Agent": f"csos-agent/{AGENT_VERSION}"},
    )
    context = ssl.create_default_context()
    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return True, response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code}: {error.read().decode(errors='replace')}"
    except (urllib.error.URLError, OSError, ssl.SSLError) as error:
        return False, f"Unable to reach CSOS: {error}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CSOS endpoint inventory reporter")
    parser.add_argument("--server")
    parser.add_argument("--api-key", dest="api_key")
    parser.add_argument("--environment", default="production")
    parser.add_argument("--criticality", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--asset-type", dest="asset_type", choices=["server", "application", "network_device", "endpoint", "workstation", "database", "cloud_resource"], default="server")
    parser.add_argument("--owner")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-packages", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    args.server = args.server or os.environ.get("CSOS_SERVER")
    args.api_key = args.api_key or os.environ.get("CSOS_API_KEY")
    if args.dry_run:
        print(json.dumps(build_report(args), indent=2, ensure_ascii=False))
        return 0
    if not args.server or not args.api_key:
        parser.error("CSOS server and API key are required")
    while True:
        report = build_report(args)
        success, message = send_report(report, args.server, args.api_key, insecure=args.insecure)
        if not success:
            print(message, file=sys.stderr)
        if not args.daemon:
            return 0 if success else 1
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
