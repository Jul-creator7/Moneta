from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./tandem.db"


class Settings(DatabaseSettings):
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    frontend_dist: Path | None = None
