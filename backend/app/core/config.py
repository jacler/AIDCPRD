from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "AIDC-CostPro"
    app_env: str = "development"
    debug: bool = True

    database_url: str = (
        "postgresql+asyncpg://aidc:aidc_dev_password@localhost:5432/aidc_costpro"
    )
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: List[str] = ["http://localhost:3000"]

    jwt_secret_key: str = "aidc-costpro-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"
    admin_display_name: str = "系统管理员"


@lru_cache
def get_settings() -> Settings:
    return Settings()
