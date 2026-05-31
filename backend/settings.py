from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "competitor-analysis-backend"
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str | None = None
    redis_url: str | None = None
    jwt_secret: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "competitor-analysis"
    mock_llm: bool = Field(default=True, validation_alias="MOCK_LLM")
    scoping_model: str = "gpt-4o-mini"
    collector_model: str = "gemini-2.5-flash"
    analyst_model: str = "deepseek-v4-pro"
    writer_model: str = "deepseek-v4-pro"
    qa_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
