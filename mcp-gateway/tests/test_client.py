import asyncio

import httpx
import pytest

from csos_mcp.client import CSOSAPIClient, CSOSAPIError


def test_client_forwards_bearer_token_and_query_parameters():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer signed-token"
        assert request.url.params["criticality"] == "critical"
        return httpx.Response(200, json=[{"id": "asset-1"}])

    client = CSOSAPIClient(
        "http://backend.test/api/v1",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        client.get(
            "/assets",
            "signed-token",
            {"criticality": "critical"},
        )
    )

    assert result == [{"id": "asset-1"}]


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (401, "expired or no longer valid"),
        (403, "role is not permitted"),
        (404, "entity was not found"),
        (503, "HTTP 503"),
    ],
)
def test_client_returns_safe_errors(status_code: int, message: str):
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"detail": "internal detail"})

    client = CSOSAPIClient(
        "http://backend.test/api/v1",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CSOSAPIError, match=message):
        asyncio.run(client.get("/assets", "signed-token"))
