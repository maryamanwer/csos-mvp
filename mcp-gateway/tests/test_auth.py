import asyncio
from datetime import datetime, timedelta, timezone

import jwt

from csos_mcp.auth import CSOSJWTVerifier
from csos_mcp.config import MCPSettings


def _settings() -> MCPSettings:
    return MCPSettings(
        MCP_JWT_SECRET_KEY="test-secret-that-is-at-least-32-bytes-long",
        MCP_JWT_ISSUER="csos-auth",
        MCP_JWT_AUDIENCE="csos-mcp",
        MCP_RESOURCE_URL="http://localhost:8001/mcp",
    )


def _token(config: MCPSettings, **overrides) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user-123",
        "role": "Analyst",
        "email": "analyst@csos.test",
        "iss": config.MCP_JWT_ISSUER,
        "aud": ["csos-platform", config.MCP_JWT_AUDIENCE],
        "type": "access",
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(
        claims,
        config.MCP_JWT_SECRET_KEY,
        algorithm=config.MCP_JWT_ALGORITHM,
    )


def test_csos_access_token_maps_to_mcp_identity_and_scopes():
    config = _settings()
    verified = asyncio.run(CSOSJWTVerifier(config).verify_token(_token(config)))

    assert verified is not None
    assert verified.subject == "user-123"
    assert verified.scopes == ["csos:read", "role:analyst"]
    assert verified.claims["email"] == "analyst@csos.test"


def test_refresh_or_wrong_audience_token_is_rejected():
    config = _settings()
    verifier = CSOSJWTVerifier(config)

    refresh = _token(config, type="refresh")
    wrong_audience = _token(config, aud="another-service")

    assert asyncio.run(verifier.verify_token(refresh)) is None
    assert asyncio.run(verifier.verify_token(wrong_audience)) is None
