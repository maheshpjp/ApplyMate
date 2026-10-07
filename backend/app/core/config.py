from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Job Application Automation Platform"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    secret_key: str = Field(
        default="change-me-in-production-please-change",
        min_length=32,
    )
    database_url: str = "postgresql+asyncpg://applymate:applymate@postgres:5432/applymate"
    redis_url: str = "redis://redis:6379/0"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "test", "testserver"]
    openai_api_key: str | None = None
    openai_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"
    browser_headless: bool = True
    job_check_interval_seconds: int = 300
    max_retries: int = 3
    request_timeout_seconds: int = 30
    max_parallel_jobs: int = 2
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    smtp_starttls: bool = True

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment.casefold() == "production":
            if self.secret_key.startswith("replace-"):
                raise ValueError("SECRET_KEY must be changed before running in production")
            if not self.allowed_hosts or any(
                host.casefold() in {"*", "localhost", "127.0.0.1"}
                for host in self.allowed_hosts
            ):
                raise ValueError("ALLOWED_HOSTS must contain only the production hostnames")
            if not self.cors_origins or any(
                not origin.casefold().startswith("https://")
                or "localhost" in origin.casefold()
                or "127.0.0.1" in origin
                for origin in self.cors_origins
            ):
                raise ValueError("CORS_ORIGINS must contain HTTPS production frontend origins")
        return self

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
