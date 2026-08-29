"""Public SDK for CSOS source adapters and normalized evidence records."""
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

# Built-ins self-register when the package loads.
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
