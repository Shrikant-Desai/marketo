# core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal, Optional

class Settings(BaseSettings):
    app_name: str = "Marketo"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Auth
    jwt_secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str
    sync_database_url: Optional[str] = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # SMTP Settings for Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None

    stripe_webhook_secret: str = ""

    enable_metrics: bool = True
    enable_tracing: bool = False

    model_config = {"env_file": ".env"}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

@lru_cache
def get_settings() -> Settings:
    return Settings()
