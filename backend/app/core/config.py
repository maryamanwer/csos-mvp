"""
Centralized application settings, loaded from environment variables (.env).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CSOS"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production-32-bytes-minimum"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "csos-auth"
    JWT_PLATFORM_AUDIENCE: str = "csos-platform"
    JWT_MCP_AUDIENCE: str = "csos-mcp"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEMO_ADMIN_EMAIL: str = "admin@csos.com"
    DEMO_ADMIN_PASSWORD: str = "csos-demo"
    MAX_IMPORT_ROWS: int = 5000

    # Collection-layer credential protection. Keep this separate from JWT
    # signing so access-token rotation never destroys stored connector secrets.
    # Multiple comma-separated values support key rotation; the first encrypts
    # new values while every configured value can decrypt existing records.
    CONNECTOR_ENCRYPTION_KEYS: str = "change-me-connector-encryption-key"
    CONNECTOR_ALLOWED_CIDRS: str = ""
    CONNECTOR_REQUEST_TIMEOUT_SECONDS: int = 30
    CONNECTOR_IMPORT_ROOT: str = "/data/imports"
    CONNECTOR_MAX_IMPORT_BYTES: int = 25_000_000
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_TICK_SECONDS: int = 60
    SYSLOG_ENABLED: bool = False
    SYSLOG_BIND_ADDRESS: str = "127.0.0.1"
    SYSLOG_UDP_PORT: int = 5514
    SYSLOG_TCP_PORT: int = 5514
    SYSLOG_MAX_MESSAGE_BYTES: int = 65536

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "csos"
    POSTGRES_USER: str = "csos"
    POSTGRES_PASSWORD: str = "csos_password"

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "csos_password"

    # AI model provider (Ollama is the default local runtime)
    AI_PROVIDER: str = "ollama"
    AI_DEFAULT_MODEL: str = "llama3.1"
    AI_AVAILABLE_MODELS: str = "llama3.1,deepseek-r1,qwen2.5,mistral,allam"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OPENAI_COMPATIBLE_BASE_URL: str = ""
    OPENAI_COMPATIBLE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def available_ai_models(self) -> tuple[str, ...]:
        """Configured model IDs that users may select at runtime."""
        return tuple(
            model.strip()
            for model in self.AI_AVAILABLE_MODELS.split(",")
            if model.strip()
        )

    @property
    def connector_encryption_keys(self) -> tuple[str, ...]:
        return tuple(
            key.strip()
            for key in self.CONNECTOR_ENCRYPTION_KEYS.split(",")
            if key.strip()
        )

    @property
    def connector_allowed_cidrs(self) -> tuple[str, ...]:
        return tuple(
            cidr.strip()
            for cidr in self.CONNECTOR_ALLOWED_CIDRS.split(",")
            if cidr.strip()
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
