# core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal, Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Marketo"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Auth
    jwt_secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str
    sync_database_url: Optional[str] = None  # for Alembic — auto-set via Docker

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # SMTP (for Celery email tasks)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None

    # Payment
    stripe_webhook_secret: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = False

    model_config = {"env_file": ".env"}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
