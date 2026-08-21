"""CSOS MCP server exposing approved, read-only platform capabilities."""
from typing import Annotated, Any
from urllib.parse import quote

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from csos_mcp.auth import CSOSJWTVerifier
from csos_mcp.client import CSOSAPIClient
from csos_mcp.config import settings


api = CSOSAPIClient(
    settings.MCP_BACKEND_URL,
    timeout_seconds=settings.MCP_REQUEST_TIMEOUT_SECONDS,
)

mcp = MCPServer(
    name=settings.MCP_SERVER_NAME,
    title="Cyber Security Operating System MCP Gateway",
    description=(
        "Authorized access to CSOS assets, correlated findings, risk, compliance, "
        "and Cyber Knowledge Graph topology."
    ),
    instructions=(
        "Use these read-only tools to ground security analysis in CSOS. "
        "Never claim that a source is live unless its returned data identifies a live adapter."
    ),
    version=settings.MCP_SERVER_VERSION,
    token_verifier=CSOSJWTVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.MCP_ISSUER_URL),
        resource_server_url=AnyHttpUrl(settings.MCP_RESOURCE_URL),
        required_scopes=["csos:read"],
    ),
)


def _bearer_token() -> str:
    access_token = get_access_token()
    if access_token is None:
        raise PermissionError("An authenticated CSOS bearer token is required.")
    return access_token.token


def _compact_params(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "")}


def _path_segment(value: str) -> str:
    return quote(value, safe="")


@mcp.tool()
async def whoami() -> dict[str, Any]:
    """Return the active CSOS user and RBAC role for this MCP connection."""
    return await api.get("/auth/me", _bearer_token())


@mcp.tool()
async def search_assets(
    search: str = "",
    asset_type: str = "",
    criticality: str = "",
    environment: str = "",
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    """Search the authorized CSOS asset inventory."""
    return await api.get(
        "/assets",
        _bearer_token(),
        _compact_params(
            search=search,
            asset_type=asset_type,
            criticality=criticality,
            environment=environment,
            limit=limit,
        ),
    )


@mcp.tool()
async def get_asset(asset_id: str) -> dict[str, Any]:
    """Read one CSOS asset record by its stable asset ID."""
    return await api.get(f"/assets/{_path_segment(asset_id)}", _bearer_token())


@mcp.tool()
async def list_security_findings(
    search: str = "",
    risk_level: str = "",
    criticality: str = "",
    severity: str = "",
    edr_coverage: str = "",
    asset_type: str = "",
    owner: str = "",
    status: str = "",
    data_source: str = "",
    page: Annotated[int, Field(ge=1)] = 1,
    page_size: Annotated[int, Field(ge=10, le=100)] = 25,
) -> dict[str, Any]:
    """List correlated findings with asset, EDR, risk, SLA, and source context."""
    return await api.get(
        "/findings",
        _bearer_token(),
        _compact_params(
            search=search,
            risk_level=risk_level,
            criticality=criticality,
            severity=severity,
            edr_coverage=edr_coverage,
            asset_type=asset_type,
            owner=owner,
            status=status,
            data_source=data_source,
            page=page,
            page_size=page_size,
        ),
    )


@mcp.tool()
async def get_security_finding(
    finding_id: str,
    asset_id: str | None = None,
) -> dict[str, Any]:
    """Investigate one finding from asset and owner through risk and remediation."""
    return await api.get(
        f"/findings/{_path_segment(finding_id)}",
        _bearer_token(),
        _compact_params(asset_id=asset_id),
    )


@mcp.tool()
async def get_topology(focus_asset_id: str | None = None) -> dict[str, Any]:
    """Read the current Neo4j Cyber Knowledge Graph topology projection."""
    return await api.get(
        "/topology",
        _bearer_token(),
        _compact_params(focus_asset_id=focus_asset_id),
    )


@mcp.tool()
async def get_executive_risk_summary() -> dict[str, Any]:
    """Read current executive risk, asset, vulnerability, and compliance KPIs."""
    return await api.get("/dashboard/executive", _bearer_token())


@mcp.tool()
async def list_top_risks(
    limit: Annotated[int, Field(ge=1, le=25)] = 5,
) -> list[dict[str, Any]]:
    """List the highest-priority CSOS risks available to the current role."""
    return await api.get("/risk/top", _bearer_token(), {"limit": limit})


@mcp.tool()
async def get_compliance_coverage() -> list[dict[str, Any]]:
    """Read framework coverage available to the current CSOS role."""
    return await api.get("/compliance/coverage", _bearer_token())


@mcp.resource("csos://findings/summary", mime_type="application/json")
async def findings_summary() -> dict[str, Any]:
    """Current CSOS security-finding and security-gap summary."""
    return await api.get("/findings/summary", _bearer_token())


@mcp.resource("csos://topology/current", mime_type="application/json")
async def current_topology() -> dict[str, Any]:
    """Current bounded Cyber Knowledge Graph projection."""
    return await api.get("/topology", _bearer_token())


@mcp.resource("csos://connectors/catalog", mime_type="application/json")
def connector_catalog() -> dict[str, Any]:
    """Connector readiness without claiming unconfigured vendors are live."""
    return {
        "active_sources": ["Neo4j Cyber Knowledge Graph", "PostgreSQL", "CSV/XLSX imports"],
        "mcp_gateway": "connected",
        "vendor_connectors": [
            {"category": "EDR / XDR", "status": "credentials_required"},
            {"category": "SIEM", "status": "credentials_required"},
            {"category": "CMDB", "status": "credentials_required"},
            {"category": "Cloud", "status": "credentials_required"},
            {"category": "Identity", "status": "credentials_required"},
        ],
    }


@mcp.prompt()
def investigate_finding(finding_id: str, asset_id: str = "") -> str:
    """Create a grounded CSOS finding-investigation instruction."""
    asset_instruction = f" for asset {asset_id}" if asset_id else ""
    return (
        f"Investigate CSOS finding {finding_id}{asset_instruction}. "
        "Call get_security_finding first, cite returned entity IDs, explain the "
        "Asset → Owner → Vulnerability → Controls → Risk → Remediation chain, "
        "and distinguish observed facts from recommendations."
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    """Unauthenticated liveness only; no private CSOS data is returned."""
    return JSONResponse(
        {
            "status": "ok",
            "service": settings.MCP_SERVER_NAME,
            "version": settings.MCP_SERVER_VERSION,
            "transport": "streamable-http",
            "authentication": "csos-jwt-bearer",
        }
    )


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=settings.MCP_DNS_REBINDING_PROTECTION,
    allowed_hosts=settings.allowed_hosts,
    allowed_origins=settings.allowed_origins,
)

app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    transport_security=transport_security,
)
