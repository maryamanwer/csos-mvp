"""CSOS adapter SDK and in-process adapter catalogue."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.connectors.models import CollectionResult


class ConnectorError(RuntimeError):
    pass


class ConfigurationError(ConnectorError):
    pass


@dataclass(frozen=True)
class ConfigField:
    name: str
    label: str
    type: str = "string"
    required: bool = True
    secret: bool = False
    default: Any = None
    help: str | None = None
    choices: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseConnector(ABC):
    key = ""
    display_name = ""
    description = ""
    category = "other"
    schedulable = True
    config_fields: tuple[ConfigField, ...] = ()

    def apply_defaults(self, config: dict[str, Any] | None) -> dict[str, Any]:
        supplied = dict(config or {})
        for field in self.config_fields:
            if supplied.get(field.name) in (None, "") and field.default is not None:
                supplied[field.name] = field.default
        return supplied

    def validate_config(self, config: dict[str, Any]) -> None:
        absent = [
            field.label
            for field in self.config_fields
            if field.required and field.default is None and config.get(field.name) in (None, "", [])
        ]
        if absent:
            raise ConfigurationError(f"Missing required fields: {', '.join(absent)}")

    def prepared_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        ready = self.apply_defaults(config)
        self.validate_config(ready)
        return ready

    def test_connection(self, config: dict[str, Any]) -> tuple[bool, str]:
        try:
            self.prepared_config(config)
        except ConfigurationError as error:
            return False, str(error)
        return True, "Configuration accepted."

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

    @abstractmethod
    def collect(self, config: dict[str, Any]) -> CollectionResult:
        raise NotImplementedError


_CATALOGUE: dict[str, type[BaseConnector]] = {}


def register_connector(adapter: type[BaseConnector]) -> type[BaseConnector]:
    key = adapter.key.strip()
    if not key:
        raise ValueError("Connector key is required")
    _CATALOGUE[key] = adapter
    return adapter


def get_connector(key: str) -> BaseConnector:
    adapter = _CATALOGUE.get(key)
    if adapter is None:
        raise ConnectorError(f"Unknown connector '{key}'")
    return adapter()


def list_connectors() -> list[dict[str, Any]]:
    return [_CATALOGUE[key].describe() for key in sorted(_CATALOGUE)]


def registered_keys() -> Iterable[str]:
    return tuple(sorted(_CATALOGUE))
