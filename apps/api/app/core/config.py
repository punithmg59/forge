from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]

INSECURE_SECRET_KEYS = frozenset({"change-me", ""})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env.example", REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://forge:forge@localhost:5433/forge"
    redis_url: str = "redis://localhost:6379/0"
    session_cookie_name: str = "forge_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 14
    cors_origins: str = "http://localhost:3000"

    llm_provider: str = "newtron"
    llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    llm_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    llm_timeout_seconds: float = 120.0
    newtron_api_key: str = ""
    newtron_base_url: str = "https://integrate.api.nvidia.com/v1"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0
    anthropic_api_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    posthog_api_key: str = ""

    tool_default_timeout_ms: int = 5000
    tool_external_timeout_ms: int = 15000
    tool_max_input_bytes: int = 8192
    tool_max_output_bytes: int = 65536
    tool_max_records: int = 100
    tool_max_calls_per_request: int = 10
    tool_max_total_execution_ms: int = 30000
    tool_allow_write_tools: bool = False

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.app_env == "production" and self.secret_key in INSECURE_SECRET_KEYS:
            raise ValueError("SECRET_KEY must be set to a secure value in production")
        return self

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
