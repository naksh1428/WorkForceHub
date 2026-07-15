"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    Values can be overridden with environment variables, e.g.
    DATABASE_URL=mysql+pymysql://user:pass@host:3306/db uvicorn app.main:app
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Employee Management API"
    version: str = "1.0.0"
    DATABASE_URL: str
    REDIS_URL: str
    CACHE_TTL_SECONDS: int = 300
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()