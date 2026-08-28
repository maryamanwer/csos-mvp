"""Generic read-only adapters for enterprise security REST APIs.

Vendors expose different JSON envelopes, but their core asset and finding
fields are remarkably consistent. These adapters provide a safe production
boundary now and keep vendor-specific field mapping in configuration instead
of coupling it to the graph writer. A dedicated vendor adapter can later
subclass the same connector without changing ingestion or the portal.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import (
    BaseConnector,
    ConfigField,
    ConfigurationError,
    register_connector,
)
from app.connectors.models import (
    CollectedAsset,
    CollectedVulnerability,
    CollectionResult,
)
from app.core.config import settings
from app.core.network_policy import TargetPolicyError, validate_connector_url


def _items(payload: Any, preferred: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in (preferred, "items", "data", "results", "value"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for nested in ("items", "results", "data"):
                if isinstance(value.get(nested), list):
                    return [item for item in value[nested] if isinstance(item, dict)]
    return []


def _first(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value: Any = row
        for part in name.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value not in (None, "", []):
            return value
    return default


def _severity(value: Any) -> str:
    text = str(value or "medium").lower().replace("informational", "low")
    return text if text in {"low", "medium", "high", "critical"} else "medium"


def _asset_type(value: Any) -> str:
    text = str(value or "server").lower().replace(" ", "_")
    aliases = {"device": "endpoint", "computer": "workstation", "host": "server"}
    text = aliases.get(text, text)
    allowed = {
        "server", "application", "network_device", "router", "switch",
        "firewall", "endpoint", "workstation", "database", "cloud_resource",
        "identity", "other",
    }
    return text if text in allowed else "other"


def _finding_status(value: Any) -> str:
    text = str(value or "open").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "closed": "resolved",
        "fixed": "resolved",
        "mitigated": "resolved",
        "accepted": "accepted_risk",
        "risk_accepted": "accepted_risk",
        "investigating": "in_progress",
    }
    text = aliases.get(text, text)
    return text if text in {"open", "in_progress", "resolved", "accepted_risk"} else "open"


class EnterpriseApiConnector(BaseConnector):
    """Base for read-only bearer/API-key JSON sources."""

    source_label = "Enterprise API"
    category = "enterprise"
    config_fields = (
        ConfigField("base_url", "Base URL", help="HTTPS URL of the vendor API"),
        ConfigField(
            "auth_mode", "Authentication", type="select",
            choices=["bearer", "api_key"], default="bearer",
        ),
        ConfigField("api_token", "API token", secret=True),
        ConfigField(
            "api_key_header", "API-key header", default="X-API-Key", required=False,
        ),
        ConfigField("assets_path", "Assets endpoint", default="/assets", required=False),
        ConfigField("findings_path", "Findings endpoint", default="/findings", required=False),
        ConfigField("health_path", "Health endpoint", required=False),
        ConfigField("environment", "Environment", default="production", required=False),
        ConfigField(
            "default_criticality", "Default criticality", type="select",
            choices=["low", "medium", "high", "critical"], default="medium",
            required=False,
        ),
        ConfigField(
            "max_records", "Maximum records per endpoint", type="number",
            default=5000, required=False,
        ),
    )

    def validate_config(self, config: dict[str, Any]) -> None:
        super().validate_config(config)
        try:
            validate_connector_url(str(config.get("base_url") or ""))
        except TargetPolicyError as exc:
            raise ConfigurationError(str(exc)) from exc
        for field in ("assets_path", "findings_path", "health_path"):
            path = str(config.get(field) or "")
            if path and (not path.startswith("/") or "://" in path):
                raise ConfigurationError(f"{field} must be a relative path beginning with /")
        if int(config.get("max_records") or 5000) > 50000:
            raise ConfigurationError("max_records cannot exceed 50000")

    @staticmethod
    def _headers(config: dict[str, Any]) -> dict[str, str]:
        token = str(config["api_token"])
        if config.get("auth_mode") == "api_key":
            return {str(config.get("api_key_header") or "X-API-Key"): token}
        return {"Authorization": f"Bearer {token}"}

    def _get(self, client: httpx.Client, path: str) -> Any:
        response = client.get(path)
        response.raise_for_status()
        return response.json()

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        config = self.apply_defaults(config)
        try:
            self.validate_config(config)
            path = str(config.get("health_path") or config.get("assets_path") or "/")
            with httpx.Client(
                base_url=str(config["base_url"]).rstrip("/"),
                headers=self._headers(config),
                timeout=settings.CONNECTOR_REQUEST_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client:
                response = client.get(path)
                response.raise_for_status()
            return True, f"Connected successfully ({response.status_code})"
        except Exception as exc:  # noqa: BLE001
            return False, f"Connection failed: {exc}"

    def collect(self, config: dict[str, Any]) -> CollectionResult:
        config = self.apply_defaults(config)
        self.validate_config(config)
        result = CollectionResult(connector_key=self.key)
        maximum = int(config.get("max_records") or 5000)

        with httpx.Client(
            base_url=str(config["base_url"]).rstrip("/"),
            headers=self._headers(config),
            timeout=settings.CONNECTOR_REQUEST_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            asset_rows: list[dict[str, Any]] = []
            finding_rows: list[dict[str, Any]] = []
            try:
                asset_rows = _items(
                    self._get(client, str(config.get("assets_path") or "/assets")),
                    "assets",
                )[:maximum]
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Asset collection failed: {exc}")
            try:
                finding_rows = _items(
                    self._get(client, str(config.get("findings_path") or "/findings")),
                    "findings",
                )[:maximum]
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Finding collection failed: {exc}")

        for row in asset_rows:
            ref = str(_first(row, "id", "asset_id", "device_id", "hostname", "name", default=""))
            if not ref:
                continue
            sources = _first(row, "data_sources", "sources", default=[])
            if not isinstance(sources, list):
                sources = [str(sources)]
            result.assets.append(CollectedAsset(
                source_ref=ref,
                name=str(_first(row, "name", "hostname", "preferred_hostname", default=ref)),
                hostname=_first(row, "hostname", "preferred_hostname", "fqdn"),
                type=_asset_type(_first(row, "type", "asset_type", "device_type")),
                criticality=_severity(_first(
                    row, "criticality", "asset_criticality",
                    default=config.get("default_criticality", "medium"),
                )),
                environment=str(_first(row, "environment", default=config.get("environment", "production"))),
                owner=_first(row, "owner", "asset_owner", "owner.name"),
                ip_address=_first(row, "ip_address", "ip", "primary_ip"),
                description=_first(row, "description"),
                vendor=_first(row, "vendor", "manufacturer"),
                model=_first(row, "model", "device_model"),
                os_name=_first(row, "operating_system", "os_name", "os.name"),
                os_version=_first(row, "os_version", "os.version"),
                serial_number=_first(row, "serial_number", "serial"),
                mac_address=_first(row, "mac_address", "mac"),
                location=_first(row, "location", "site"),
                edr_status=_first(row, "edr_status", "agent_status"),
                edr_product=_first(row, "edr_product", "agent_product"),
                edr_agent_version=_first(row, "edr_agent_version", "agent_version"),
                managed_status=_first(row, "managed_status", "management_status"),
                data_sources=[*sources, self.source_label],
                raw=row,
            ))

        for row in finding_rows:
            asset_ids = _first(row, "asset_ids", "assets", default=[])
            if not isinstance(asset_ids, list):
                single = _first(row, "asset_id", "device_id", "hostname")
                asset_ids = [single] if single else []
            sources = _first(row, "data_sources", "sources", default=[])
            if not isinstance(sources, list):
                sources = [str(sources)]
            result.vulnerabilities.append(CollectedVulnerability(
                title=str(_first(row, "title", "name", "cve", default="Security finding")),
                severity=_severity(_first(row, "severity", "risk_level")),
                cvss_score=float(_first(row, "cvss_score", "cvss", default=0) or 0),
                cve_id=_first(row, "cve_id", "cve"),
                status=_finding_status(_first(row, "status", default="open")),
                description=_first(row, "description", "details"),
                asset_refs=[str(value) for value in asset_ids if value],
                port=_first(row, "port"),
                service=_first(row, "service"),
                first_detected=_first(row, "first_detected", "created_at"),
                last_seen=_first(row, "last_seen", "updated_at"),
                sla_due_at=_first(row, "sla_due_at", "due_at"),
                recommended_remediation=_first(row, "recommended_remediation", "remediation", "solution"),
                data_sources=[*sources, self.source_label],
                vendor_finding_id=str(_first(row, "id", "finding_id", default="")) or None,
            ))

        result.finished_at = datetime.now(timezone.utc).isoformat()
        if not result.assets and not result.vulnerabilities and result.errors:
            raise RuntimeError("; ".join(result.errors))
        return result


def _register_profile(key: str, name: str, category: str, label: str) -> None:
    connector = type(
        f"{key.title().replace('_', '')}Connector",
        (EnterpriseApiConnector,),
        {
            "key": key,
            "display_name": name,
            "description": f"Read-only {label} REST collection into the CSOS correlation model.",
            "category": category,
            "source_label": label,
        },
    )
    register_connector(connector)


for _profile in (
    ("edr_xdr_api", "EDR / XDR API", "endpoint", "EDR / XDR"),
    ("siem_api", "SIEM API", "log", "SIEM"),
    ("cmdb_api", "CMDB API", "inventory", "CMDB"),
    ("identity_api", "Identity / Directory API", "identity", "Identity"),
    ("cloud_api", "Cloud Platform API", "cloud", "Cloud platform"),
    ("firewall_api", "Firewall Manager API", "network", "Firewall"),
    ("patch_api", "Patch Management API", "endpoint", "Patch Management"),
):
    _register_profile(*_profile)
