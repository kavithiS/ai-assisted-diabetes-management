"""Base settings shared by every server package. Values come from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Settings common to the gateway and all services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    database_url: str = "postgresql://diacare:change-me@localhost:5432/diacare"
    mlflow_tracking_uri: str = "http://localhost:5000"
