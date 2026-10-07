"""App settings, read from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app settings. Change any of them with an environment variable or the .env file."""
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