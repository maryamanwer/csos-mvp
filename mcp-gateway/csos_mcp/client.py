"""Small authenticated client for the CSOS REST boundary."""
from typing import Any

import httpx


class CSOSAPIError(RuntimeError):
    """A safe error suitable for returning through an MCP tool result."""


class CSOSAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def get(
        self,
        path: str,
        token: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
                transport=self.transport,
            ) as client:
                response = await client.get(path, headers=headers, params=params)
        except httpx.RequestError as exc:
            raise CSOSAPIError("The CSOS backend is currently unavailable.") from exc

        if response.status_code == 401:
            raise CSOSAPIError("The CSOS access token is expired or no longer valid.")
        if response.status_code == 403:
            raise CSOSAPIError("The current CSOS role is not permitted to use this capability.")
        if response.status_code == 404:
            raise CSOSAPIError("The requested CSOS entity was not found.")
        if response.is_error:
            raise CSOSAPIError(
                f"The CSOS backend returned HTTP {response.status_code}."
            )
        return response.json()
