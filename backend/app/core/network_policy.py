"""Outbound target policy for credentialed collection connectors."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings


class TargetPolicyError(ValueError):
    """Raised when a connector target is unsafe or outside its allow-list."""


BLOCKED_EXACT = {
    ipaddress.ip_address("169.254.169.254"),  # common cloud metadata service
    ipaddress.ip_address("100.100.100.200"),  # Alibaba metadata service
}


def _allowed_networks() -> tuple[ipaddress._BaseNetwork, ...]:
    networks = []
    for value in settings.connector_allowed_cidrs:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise TargetPolicyError(f"Invalid CONNECTOR_ALLOWED_CIDRS entry: {value}") from exc
    return tuple(networks)


def _resolve(host: str) -> set[ipaddress._BaseAddress]:
    value = host.strip().strip("[]")
    if not value:
        raise TargetPolicyError("Connector target is required")
    try:
        return {ipaddress.ip_address(value)}
    except ValueError:
        try:
            return {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(value, None, type=socket.SOCK_STREAM)
            }
        except socket.gaierror as exc:
            raise TargetPolicyError(f"Connector target cannot be resolved: {host}") from exc


def validate_connector_target(host: str) -> str:
    """Reject local/metadata targets and optionally require configured CIDRs."""
    addresses = _resolve(host)
    allowed = _allowed_networks()
    for address in addresses:
        if (
            address in BLOCKED_EXACT
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
        ):
            raise TargetPolicyError(f"Connector target is blocked by policy: {host}")
        if allowed and not any(address in network for network in allowed):
            raise TargetPolicyError(f"Connector target is outside CONNECTOR_ALLOWED_CIDRS: {host}")
    return host


def validate_connector_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise TargetPolicyError("Connector URL must use http or https and include a host")
    validate_connector_target(parsed.hostname)
    return url
