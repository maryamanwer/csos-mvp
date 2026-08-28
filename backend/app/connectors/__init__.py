"""Connector subsystem.

Importing this package registers every built-in connector. Adding a new data
source means dropping a module here that calls ``register_connector`` and
listing it below — nothing else in the codebase changes.
"""
from app.connectors.base import (  # noqa: F401
    BaseConnector,
    ConfigField,
    ConfigurationError,
    ConnectorError,
    get_connector,
    list_connectors,
    register_connector,
    registered_keys,
)
from app.connectors.models import (  # noqa: F401
    CollectedAsset,
    CollectedEvent,
    CollectedInterface,
    CollectedLink,
    CollectedVulnerability,
    CollectionResult,
)

# Import for side effect: each module registers its connector on import.
from app.connectors import agent_ingest  # noqa: F401,E402
from app.connectors import enterprise_api  # noqa: F401,E402
from app.connectors import nmap_scan  # noqa: F401,E402
from app.connectors import snmp  # noqa: F401,E402
from app.connectors import ssh_network  # noqa: F401,E402
from app.connectors import syslog  # noqa: F401,E402

__all__ = [
    "BaseConnector",
    "ConfigField",
    "ConfigurationError",
    "ConnectorError",
    "CollectedAsset",
    "CollectedEvent",
    "CollectedInterface",
    "CollectedLink",
    "CollectedVulnerability",
    "CollectionResult",
    "get_connector",
    "list_connectors",
    "register_connector",
    "registered_keys",
]
