import asyncio
import time

import jwt
from mcp import Client
import pytest
from starlette.testclient import TestClient

import csos_mcp.server as server_module
from csos_mcp.config import settings
from csos_mcp.server import app, mcp


@pytest.fixture(scope="module")
def gateway_client():
    with TestClient(app) as client:
        yield client


def _access_token() -> str:
    return jwt.encode(
        {
            "sub": "user-123",
            "role": "Analyst",
            "email": "analyst@csos.test",
            "iss": settings.MCP_JWT_ISSUER,
            "aud": ["csos-platform", settings.MCP_JWT_AUDIENCE],
            "type": "access",
            "exp": int(time.time()) + 300,
        },
        settings.MCP_JWT_SECRET_KEY,
        algorithm=settings.MCP_JWT_ALGORITHM,
    )


def test_gateway_advertises_approved_read_only_tools_and_resources():
    async def inspect_server():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            return (
                {tool.name for tool in tools.tools},
                {str(resource.uri) for resource in resources.resources},
                {prompt.name for prompt in prompts.prompts},
            )

    tool_names, resource_uris, prompt_names = asyncio.run(inspect_server())

    assert tool_names == {
        "whoami",
        "search_assets",
        "get_asset",
        "list_security_findings",
        "get_security_finding",
        "get_topology",
        "list_attack_paths",
        "list_data_sources",
        "get_ai_runtime_status",
        "get_executive_risk_summary",
        "list_top_risks",
        "get_compliance_coverage",
    }
    assert resource_uris == {
        "csos://findings/summary",
        "csos://topology/current",
        "csos://connectors/catalog",
    }
    assert prompt_names == {"investigate_finding"}


def test_health_is_public_but_mcp_endpoint_requires_bearer_authentication(gateway_client):
    health = gateway_client.get("/health")
    unauthorized = gateway_client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        },
    )

    assert health.status_code == 200
    assert health.json()["transport"] == "streamable-http"
    assert unauthorized.status_code == 401


def test_signed_csos_token_initializes_streamable_http_connection(gateway_client):
    token = _access_token()

    response = gateway_client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "csos-test", "version": "1.0"},
            },
        },
    )
    tools_response = gateway_client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )

    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "CSOS MCP Gateway"
    assert tools_response.status_code == 200
    assert "get_topology" in {
        tool["name"] for tool in tools_response.json()["result"]["tools"]
    }


def test_authenticated_tool_call_forwards_the_same_csos_token(
    gateway_client,
    monkeypatch,
):
    calls = []

    class FakeAPI:
        async def get(self, path, token, params=None):
            calls.append((path, token, params))
            return [{"id": "asset-1", "criticality": "critical"}]

    token = _access_token()
    monkeypatch.setattr(server_module, "api", FakeAPI())
    response = gateway_client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_assets",
                "arguments": {"criticality": "critical", "limit": 10},
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["result"]["isError"] is False
    assert calls == [
        ("/assets", token, {"criticality": "critical", "limit": 10})
    ]
