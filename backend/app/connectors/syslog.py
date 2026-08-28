"""Syslog reception and parsing.

Syslog is push-based: devices send to us, so there is nothing to poll. The
connector class exists to describe and configure the listener; the actual
socket server lives in ``app.workers.syslog_server``.

Both wire formats are handled — RFC 3164 (the older BSD format still emitted by
most network gear) and RFC 5424 (the structured replacement). Anything that
matches neither is still recorded, with the whole line kept as the message, so
an unparseable format never means a silently dropped log.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, ConfigField, register_connector
from app.connectors.models import CollectedAsset, CollectedEvent, CollectionResult

SEVERITY_NAMES = {
    0: "emergency", 1: "alert", 2: "critical", 3: "error",
    4: "warning", 5: "notice", 6: "informational", 7: "debug",
}

FACILITY_NAMES = {
    0: "kernel", 1: "user", 2: "mail", 3: "daemon", 4: "auth", 5: "syslog",
    6: "lpr", 7: "news", 8: "uucp", 9: "cron", 10: "authpriv", 11: "ftp",
    16: "local0", 17: "local1", 18: "local2", 19: "local3",
    20: "local4", 21: "local5", 22: "local6", 23: "local7",
}

#: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD] MSG
RFC5424_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<version>\d)\s+"
    r"(?P<timestamp>\S+)\s+(?P<hostname>\S+)\s+(?P<app>\S+)\s+"
    r"(?P<procid>\S+)\s+(?P<msgid>\S+)\s+"
    r"(?P<rest>.*)$",
    re.DOTALL,
)

#: <PRI>MMM dd HH:MM:SS HOSTNAME TAG: MSG
RFC3164_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<rest>.*)$",
    re.DOTALL,
)

TAG_RE = re.compile(r"^(?P<app>[\w\-./]+)(?:\[(?P<pid>\d+)\])?:\s*(?P<msg>.*)$", re.DOTALL)


def decode_priority(pri: int) -> tuple[str, str]:
    """Split a syslog PRI value into facility and severity names."""
    facility = FACILITY_NAMES.get(pri // 8, str(pri // 8))
    severity = SEVERITY_NAMES.get(pri % 8, str(pri % 8))
    return facility, severity


def parse_syslog_line(line: str, source_ip: str | None = None) -> CollectedEvent:
    """Parse one syslog line into a canonical event.

    Never raises: a line that matches no known format is returned as a
    best-effort event with the raw text preserved.
    """
    raw = (line or "").strip()
    if not raw:
        return CollectedEvent(message="", source_ip=source_ip, raw=line)

    match = RFC5424_RE.match(raw)
    if match:
        facility, severity = decode_priority(int(match.group("pri")))
        rest = match.group("rest").strip()
        # Structured data, when present, is a bracketed block before the message.
        if rest.startswith("["):
            depth, index = 0, 0
            for index, char in enumerate(rest):
                if char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                    if depth == 0:
                        break
            rest = rest[index + 1 :].strip()
        elif rest.startswith("-"):
            rest = rest[1:].strip()
        hostname = match.group("hostname")
        app = match.group("app")
        return CollectedEvent(
            message=rest,
            source_ref=hostname if hostname != "-" else None,
            source_ip=source_ip,
            severity=severity,
            facility=facility,
            hostname=None if hostname == "-" else hostname,
            app_name=None if app == "-" else app,
            timestamp=_normalize_timestamp(match.group("timestamp")),
            raw=raw,
        )

    match = RFC3164_RE.match(raw)
    if match:
        facility, severity = decode_priority(int(match.group("pri")))
        rest = match.group("rest").strip()
        app, message = None, rest
        tag_match = TAG_RE.match(rest)
        if tag_match:
            app = tag_match.group("app")
            message = tag_match.group("msg")
        hostname = match.group("hostname")
        return CollectedEvent(
            message=message,
            source_ref=hostname,
            source_ip=source_ip,
            severity=severity,
            facility=facility,
            hostname=hostname,
            app_name=app,
            timestamp=_normalize_timestamp(match.group("timestamp")),
            raw=raw,
        )

    return CollectedEvent(
        message=raw, source_ip=source_ip, hostname=None, raw=raw
    )


def _normalize_timestamp(value: str) -> str:
    """Return an ISO-8601 timestamp, falling back to now when unparseable."""
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        # RFC 3164 omits the year entirely.
        parsed = datetime.strptime(value, "%b %d %H:%M:%S")
        return parsed.replace(
            year=datetime.now(timezone.utc).year, tzinfo=timezone.utc
        ).isoformat()
    except (ValueError, TypeError):
        return datetime.now(timezone.utc).isoformat()


def events_to_result(events: list[CollectedEvent]) -> CollectionResult:
    """Turn received events into a result, inferring assets from senders.

    A device that sends logs is a device that exists — so each distinct sender
    becomes an asset. This makes syslog a discovery source, not just a log sink.
    """
    result = CollectionResult(connector_key="syslog")
    result.events = events

    seen: dict[str, CollectedAsset] = {}
    for event in events:
        from app.connectors.ssh_network import normalize_device_id

        ref = normalize_device_id(event.hostname) or (event.source_ip or "")
        if not ref or ref in seen:
            continue
        seen[ref] = CollectedAsset(
            source_ref=ref,
            name=event.hostname or event.source_ip or ref,
            type="server",
            criticality="medium",
            ip_address=event.source_ip,
            description="Discovered from emitted Syslog messages",
            tags=["syslog", "discovered"],
        )
    result.assets = list(seen.values())
    return result


@register_connector
class SyslogConnector(BaseConnector):
    key = "syslog"
    display_name = "Syslog Receiver"
    description = (
        "Receives device and server logs over UDP/TCP and extracts events and assets."
    )
    category = "log"
    schedulable = False

    config_fields = (
        ConfigField("enabled", "Enabled", type="boolean", default=True, required=False),
        ConfigField("udp_port", "UDP port", type="number", default=5514, required=False),
        ConfigField("tcp_port", "TCP port", type="number", default=5514, required=False),
        ConfigField(
            "bind_address", "Bind address", default="0.0.0.0", required=False
        ),
        ConfigField(
            "create_assets",
            "Create assets from senders",
            type="boolean",
            default=True,
            required=False,
        ),
    )

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        """Syslog is push-based; the listener writes as messages arrive."""
        result = CollectionResult(connector_key=self.key)
        result.errors.append(
            "Syslog is push-based and is accepted by the dedicated worker"
        )
        return result

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        config = self.apply_defaults(config)
        udp = config.get("udp_port", 5514)
        tcp = config.get("tcp_port", 5514)
        return True, f"Receiver configured for UDP:{udp} and TCP:{tcp}"
