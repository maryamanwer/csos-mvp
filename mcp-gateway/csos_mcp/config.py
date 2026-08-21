"""Environment-backed MCP gateway settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    MCP_SERVER_NAME: str = "CSOS MCP Gateway"
    MCP_SERVER_VERSION: str = "0.3.0"
    MCP_BACKEND_URL: str = "http://backend:8000/api/v1"
    MCP_ISSUER_URL: str = "http://localhost:8000/api/v1/auth"
    MCP_RESOURCE_URL: str = "http://localhost:8001/mcp"

    MCP_JWT_SECRET_KEY: str = "change-me-in-production-32-bytes-minimum"
    MCP_JWT_ALGORITHM: str = "HS256"
    MCP_JWT_ISSUER: str = "csos-auth"
    MCP_JWT_AUDIENCE: str = "csos-mcp"

    MCP_DNS_REBINDING_PROTECTION: bool = False
    MCP_ALLOWED_HOSTS: str = "localhost:*,127.0.0.1:*,mcp-gateway:8001"
    MCP_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8001"

    MCP_REQUEST_TIMEOUT_SECONDS: float = 20.0

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return self._split_csv(self.MCP_ALLOWED_HOSTS)

    @property
    def allowed_origins(self) -> list[str]:
        return self._split_csv(self.MCP_ALLOWED_ORIGINS)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = MCPSettings()
