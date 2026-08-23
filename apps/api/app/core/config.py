from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://forge:forge@localhost:5432/forge"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    posthog_api_key: str = ""


settings = Settings()
