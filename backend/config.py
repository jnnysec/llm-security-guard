import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db: str = os.getenv("POSTGRES_DB", "llm_security")
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    use_external_services: bool = _as_bool(os.getenv("USE_EXTERNAL_SERVICES", "false"))
    classifier_threshold: int = int(os.getenv("CLASSIFIER_THRESHOLD", "55"))


settings = Settings()

# Backwards-compatible constants for older imports.
POSTGRES_USER = settings.postgres_user
POSTGRES_PASSWORD = settings.postgres_password
POSTGRES_DB = settings.postgres_db
POSTGRES_HOST = settings.postgres_host
POSTGRES_PORT = settings.postgres_port
REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port
