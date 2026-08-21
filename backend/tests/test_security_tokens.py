import pytest
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token


def test_access_token_is_valid_for_platform_and_mcp_resource_server():
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        role="Analyst",
        email="analyst@csos.test",
    )

    platform_claims = decode_token(token)
    mcp_claims = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_MCP_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )

    assert platform_claims["type"] == "access"
    assert set(mcp_claims["aud"]) == {
        settings.JWT_PLATFORM_AUDIENCE,
        settings.JWT_MCP_AUDIENCE,
    }
    assert mcp_claims["role"] == "Analyst"


def test_refresh_token_is_not_valid_for_mcp_audience():
    token = create_refresh_token("00000000-0000-0000-0000-000000000001")

    claims = decode_token(token)
    assert claims["type"] == "refresh"
    with pytest.raises(JWTError):
        jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_MCP_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
