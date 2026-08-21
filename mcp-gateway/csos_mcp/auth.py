"""Validate CSOS access tokens at the MCP resource-server boundary."""
from typing import Any

import jwt
from mcp.server.auth.provider import AccessToken

from csos_mcp.config import MCPSettings, settings


class CSOSJWTVerifier:
    """Map a signed CSOS access JWT to MCP authorization context."""

    def __init__(self, config: MCPSettings = settings):
        self.config = config

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self.config.MCP_JWT_SECRET_KEY,
                algorithms=[self.config.MCP_JWT_ALGORITHM],
                audience=self.config.MCP_JWT_AUDIENCE,
                issuer=self.config.MCP_JWT_ISSUER,
                options={"require": ["exp", "sub", "type", "role", "aud", "iss"]},
            )
        except jwt.PyJWTError:
            return None

        if claims.get("type") != "access":
            return None

        subject = str(claims["sub"])
        role = str(claims["role"])
        return AccessToken(
            token=token,
            client_id=f"csos-user:{subject}",
            subject=subject,
            scopes=["csos:read", f"role:{role.lower()}"],
            expires_at=int(claims["exp"]),
            resource=self.config.MCP_RESOURCE_URL,
            claims={
                "iss": claims["iss"],
                "role": role,
                "email": claims.get("email"),
            },
        )
