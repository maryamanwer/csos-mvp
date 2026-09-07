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
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEMO_ADMIN_EMAIL: str = "admin@csos.com"
    DEMO_ADMIN_PASSWORD: str = "csos-demo"
    MAX_IMPORT_ROWS: int = 5000
    REPORT_DIRECTORY: str = "./data/reports"

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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
