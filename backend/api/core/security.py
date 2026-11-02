"""JWT, refresh-token and cookie helpers."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Response

from api.core.config import get_settings
from api.core.errors import ApiError

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def create_access_token(user) -> tuple[str, int]:
    """Return (signed JWT, lifetime in seconds)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=s.access_token_minutes)
    payload = {
        "sub": str(user.pk),
        "role": user.role,
        "ver": user.token_version,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(
            token,
            s.jwt_secret,
            algorithms=[s.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.")
    except jwt.PyJWTError:
        raise ApiError(401, "invalid_token", "Invalid authentication token.")


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    """Return (raw token for the cookie, hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _set(response: Response, key: str, value: str, max_age: int, path: str = "/") -> None:
    s = get_settings()
    response.set_cookie(
        key, value, max_age=max_age, path=path, httponly=True,
        secure=s.cookie_secure, samesite=s.cookie_samesite, domain=s.cookie_domain,
    )


def set_auth_cookies(response: Response, access: str, access_seconds: int, refresh: str, csrf: str) -> None:
    s = get_settings()
    _set(response, ACCESS_COOKIE, access, access_seconds)
    _set(response, REFRESH_COOKIE, refresh, s.refresh_token_days * 86400, REFRESH_COOKIE_PATH)
    _set(response, CSRF_COOKIE, csrf, s.refresh_token_days * 86400)


def clear_auth_cookies(response: Response) -> None:
    s = get_settings()
    for key, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, REFRESH_COOKIE_PATH), (CSRF_COOKIE, "/")):
        response.delete_cookie(key, path=path, domain=s.cookie_domain)
