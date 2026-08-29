"""Small, loss-aware parser for RFC 3164 and RFC 5424 messages."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, ConfigField, register_connector
from app.connectors.models import CollectedAsset, CollectedEvent, CollectionResult

_FACILITIES = [
    "kernel", "user", "mail", "daemon", "auth", "syslog", "printer", "news",
    "uucp", "clock", "authpriv", "ftp", "ntp", "audit", "alert", "clock2",
] + [f"local{i}" for i in range(8)]
_SEVERITIES = ["emergency", "alert", "critical", "error", "warning", "notice", "info", "debug"]
_PRI = re.compile(r"^<(?P<priority>\d{1,3})>(?P<body>.*)$", re.DOTALL)
_RFC5424 = re.compile(
    r"^(?P<version>\d+)\s+(?P<time>\S+)\s+(?P<host>\S+)\s+(?P<app>\S+)\s+"
    r"\S+\s+\S+\s+(?P<data>-|\[(?:[^\]]|\][^\s])*\])(?:\s+(?P<message>.*))?$"
)
_RFC3164 = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<message>.*)$"
)


def decode_priority(pri: int) -> tuple[str, str]:
    facility_index, severity_index = divmod(max(0, pri), 8)
    facility = _FACILITIES[facility_index] if facility_index < len(_FACILITIES) else "unknown"
    severity = _SEVERITIES[severity_index] if severity_index < len(_SEVERITIES) else "unknown"
    return facility, severity


def _source_ref(hostname: str | None, source_ip: str | None) -> str | None:
    if hostname and hostname != "-":
        return hostname.split(".", 1)[0].upper()
    return source_ip


def parse_syslog_line(line: str, source_ip: str | None = None) -> CollectedEvent:
    raw = line.strip()
    priority_match = _PRI.match(raw)
    body = priority_match.group("body") if priority_match else raw
    facility, severity = decode_priority(int(priority_match.group("priority"))) if priority_match else (None, None)

    modern = _RFC5424.match(body)
    if modern:
        parts = modern.groupdict()
        host = parts["host"] if parts["host"] != "-" else None
        app = parts["app"] if parts["app"] != "-" else None
        return CollectedEvent(
            message=parts.get("message") or "",
            source_ref=_source_ref(host, source_ip), source_ip=source_ip,
            severity=severity, facility=facility, hostname=host, app_name=app,
            timestamp=parts["time"], raw=raw,
        )

    legacy = _RFC3164.match(body)
    if legacy:
        parts = legacy.groupdict()
        host = parts["host"]
        timestamp = f"{datetime.now(timezone.utc).year} {parts['month']} {parts['day']} {parts['time']}"
        return CollectedEvent(
            message=parts["message"], source_ref=_source_ref(host, source_ip),
            source_ip=source_ip, severity=severity, facility=facility,
            hostname=host, timestamp=timestamp, raw=raw,
        )
    return CollectedEvent(message=body, source_ip=source_ip, severity=severity, facility=facility, raw=raw)


def events_to_result(events: list[CollectedEvent]) -> CollectionResult:
    result = CollectionResult(connector_key="syslog", events=list(events))
    discovered: dict[str, CollectedAsset] = {}
    for event in events:
        ref = event.source_ref or _source_ref(event.hostname, event.source_ip)
        if not ref or ref in discovered:
            continue
        discovered[ref] = CollectedAsset(
            source_ref=ref, name=event.hostname or event.source_ip or ref,
            hostname=event.hostname, ip_address=event.source_ip,
            description="Observed as a Syslog sender", data_sources=["Syslog"],
            tags=["syslog-observed", "discovered"],
        )
    result.assets.extend(discovered.values())
    return result


@register_connector
class SyslogConnector(BaseConnector):
    key = "syslog"
    display_name = "Syslog receiver"
    description = "Normalizes events received by the CSOS log listener."
    category = "log"
    schedulable = False
    config_fields = (
        ConfigField("enabled", "Enabled", type="boolean", required=False, default=True),
        ConfigField("udp_port", "UDP port", type="number", required=False, default=5514),
        ConfigField("tcp_port", "TCP port", type="number", required=False, default=5514),
        ConfigField("bind_address", "Bind address", required=False, default="0.0.0.0"),
        ConfigField("create_assets", "Create sender assets", type="boolean", required=False, default=True),
    )

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        result = CollectionResult(connector_key=self.key)
        result.errors.append("Syslog is handled continuously by the listener service")
        return result

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        ready = self.apply_defaults(config)
        return True, f"Receiver configured for UDP:{ready['udp_port']} and TCP:{ready['tcp_port']}"
