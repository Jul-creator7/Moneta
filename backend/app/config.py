from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_database_url(settings: dict) -> str:
    directory = settings["database_directory"]
    current = directory / "moneta.db"
    legacy = directory / "tandem.db"
    database = legacy if not current.exists() and legacy.is_file() else current
    return f"sqlite:///{database.as_posix()}"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_directory: Path = Path(".")
    database_url: str = Field(default_factory=default_database_url)


class Settings(DatabaseSettings):
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    frontend_dist: Path | None = None
