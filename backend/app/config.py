from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./tandem.db"


class Settings(DatabaseSettings):
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
