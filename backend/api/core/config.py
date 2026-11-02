"""FastAPI settings read from environment variables (never hardcoded)."""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class ApiSettings:
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    refresh_token_days: int
    cors_origins: list[str]
    cookie_secure: bool
    cookie_samesite: str
    cookie_domain: str | None
    enable_bearer_token_endpoint: bool


@lru_cache
def get_settings() -> ApiSettings:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or too short. Set a random value of at least 32 characters in backend/.env."
        )
    if secret == os.environ.get("DJANGO_SECRET_KEY"):
        raise RuntimeError("JWT_SECRET must be different from DJANGO_SECRET_KEY.")
    origins = _list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must list explicit origins; '*' is not allowed.")
    return ApiSettings(
        jwt_secret=secret,
        jwt_algorithm="HS256",
        access_token_minutes=int(os.environ.get("ACCESS_TOKEN_MINUTES", "15")),
        refresh_token_days=int(os.environ.get("REFRESH_TOKEN_DAYS", "7")),
        cors_origins=origins,
        cookie_secure=_bool("COOKIE_SECURE", False),
        cookie_samesite=os.environ.get("COOKIE_SAMESITE", "lax").lower(),
        cookie_domain=os.environ.get("COOKIE_DOMAIN") or None,
        enable_bearer_token_endpoint=_bool("ENABLE_BEARER_TOKEN_ENDPOINT", True),
    )
