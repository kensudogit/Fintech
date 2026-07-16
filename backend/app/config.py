from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db_url import to_asyncpg_url, to_sync_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Fintech AI Platform"
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "*"

    database_url: str = "postgresql+asyncpg://fintech:fintech_secret@127.0.0.1:15432/fintech_ai"
    database_url_sync: str = "postgresql://fintech:fintech_secret@127.0.0.1:15432/fintech_ai"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return to_asyncpg_url(value)
        return value

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def normalize_sync_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return to_sync_url(value)
        return value

    llm_provider: str = "mock"
    openai_api_key: str = ""
    google_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    knowledge_dir: str = "./data/knowledge"
    vector_collection: str = "fintech_knowledge"
    rag_top_k: int = 5

    personalization_window_days: int = 90
    min_events_for_profile: int = 5

    gcp_project_id: str = ""
    gcp_region: str = "asia-northeast1"
    gcp_credentials_path: str = "./gcp/credentials.json"
    gcs_bucket: str = ""
    cloud_sql_instance: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def knowledge_path(self) -> Path:
        path = Path(self.knowledge_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
