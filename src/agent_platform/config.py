"""Central, typed configuration loaded from environment variables / .env."""

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM ---
    groq_api_key: SecretStr
    primary_model: str = "groq/openai/gpt-oss-120b"
    fallback_model: str = "groq/llama-3.3-70b-versatile"

    # --- Database ---
    postgres_user: str = "agent"
    postgres_password: SecretStr
    postgres_db: str = "northwind"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @field_validator("groq_api_key", "postgres_password")
    @classmethod
    def must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("must not be empty — set it in .env")
        return v

    @property
    def database_url(self) -> str:
        pw = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{pw}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Create settings once and reuse them everywhere."""
    return Settings()
