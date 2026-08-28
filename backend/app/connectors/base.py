"""Connector contract and registry.

This is the extension point that makes CSOS a platform rather than an
application: a new data source is added by writing one subclass and calling
``register_connector`` — no change to the API layer, the graph writer, the
scheduler, or the UI.

The pattern deliberately mirrors ``app.ai.providers.register_model_provider``
so the codebase has one way of registering pluggable components.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from app.connectors.models import CollectionResult


class ConnectorError(RuntimeError):
    """Raised when a connector cannot complete a collection run."""


class ConfigurationError(ConnectorError):
    """Raised when a connector is given an invalid or incomplete configuration."""


class ConfigField:
    """One configuration input a connector needs.

    Declared rather than hard-coded so the UI can render a form for any
    connector — including ones written after the UI shipped.
    """

    def __init__(
        self,
        name: str,
        label: str,
        *,
        type: str = "string",
        required: bool = True,
        secret: bool = False,
        default: Any = None,
        help: str | None = None,
        choices: list[str] | None = None,
    ) -> None:
        self.name = name
        self.label = label
        self.type = type
        self.required = required
        self.secret = secret
        self.default = default
        self.help = help
        self.choices = choices

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "secret": self.secret,
            "default": self.default,
            "help": self.help,
            "choices": self.choices,
        }


class BaseConnector(ABC):
    """Every data source implements this interface."""

    #: Stable machine identifier, e.g. ``"ssh_network"``.
    key: str = ""
    #: Human-readable name shown in the UI.
    display_name: str = ""
    #: One-line description of what this connector collects.
    description: str = ""
    #: Grouping used by the UI: network, endpoint, scanner, log, file, cloud.
    category: str = "other"
    #: Whether the scheduler may run this connector on an interval. Push-based
    #: sources (syslog, agent) set this to False.
    schedulable: bool = True

    #: Configuration inputs this connector requires.
    config_fields: tuple[ConfigField, ...] = ()

    @abstractmethod
    def collect(self, config: dict[str, Any]) -> CollectionResult:
        """Gather data from the source and return it in canonical form.

        Implementations must not raise for partial failures — a device that is
        unreachable belongs in ``result.errors`` so the rest of the run still
        lands. Raise :class:`ConnectorError` only when nothing can be collected.
        """

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        """Verify the configuration without performing a full collection."""
        try:
            self.validate_config(config)
        except ConfigurationError as exc:
            return False, str(exc)
        return True, "Configuration is valid; this connector has no active connection test."

    def validate_config(self, config: dict[str, Any]) -> None:
        """Raise :class:`ConfigurationError` if a required field is missing."""
        missing = [
            field.label
            for field in self.config_fields
            if field.required
            and config.get(field.name) in (None, "", [])
            and field.default is None
        ]
        if missing:
            raise ConfigurationError("Missing required fields: " + ", ".join(missing))

    def apply_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        merged = {
            field.name: field.default
            for field in self.config_fields
            if field.default is not None
        }
        merged.update({k: v for k, v in (config or {}).items() if v not in (None, "")})
        return merged

    @classmethod
    def describe(cls) -> dict[str, Any]:
        return {
            "key": cls.key,
            "display_name": cls.display_name,
            "description": cls.description,
            "category": cls.category,
            "schedulable": cls.schedulable,
            "config_fields": [field.to_dict() for field in cls.config_fields],
        }


_registry: dict[str, type[BaseConnector]] = {}


def register_connector(connector_cls: type[BaseConnector]) -> type[BaseConnector]:
    """Register a connector class. Usable as a decorator."""
    if not connector_cls.key:
        raise ValueError("A connector must define a non-empty key")
    _registry[connector_cls.key] = connector_cls
    return connector_cls


def get_connector(key: str) -> BaseConnector:
    try:
        return _registry[key]()
    except KeyError as exc:
        available = ", ".join(sorted(_registry)) or "none"
        raise ConnectorError(
            f"Unknown connector '{key}'. Available: {available}"
        ) from exc


def list_connectors() -> list[dict[str, Any]]:
    return [cls.describe() for cls in sorted(_registry.values(), key=lambda c: c.key)]


def registered_keys() -> Iterable[str]:
    return sorted(_registry)
