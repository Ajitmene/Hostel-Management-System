"""Authentication and authorization dependencies.

The role is ALWAYS read from the database. The role claim inside the JWT is only
cross-checked, never trusted.
"""
import hmac

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from accounts.models import Role, User
from api.core.db import with_db_cleanup
from api.core.errors import ApiError
from api.core.security import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, decode_access_token

bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@with_db_cleanup
def get_current_user(request: Request, bearer: str | None = Depends(bearer_scheme)) -> User:
    token = bearer or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise ApiError(401, "not_authenticated", "Authentication required.")
    claims = decode_access_token(token)
    try:
        user = User.objects.select_related("employee_profile").get(pk=int(claims["sub"]))
    except (User.DoesNotExist, ValueError):
        raise ApiError(401, "invalid_token", "Invalid authentication token.")
    if not user.is_active:
        raise ApiError(401, "account_inactive", "This account has been deactivated.")
    if claims.get("ver") != user.token_version or claims.get("role") != user.role:
        raise ApiError(401, "token_revoked", "Your session is no longer valid. Please sign in again.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise ApiError(403, "forbidden", "Only administrators can perform this action.")
    return user


def require_permission(code: str):
    """Allow administrators, and employees who were granted `code`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_app_permission(code):
            raise ApiError(403, "forbidden", "You do not have permission to perform this action.")
        return user

    return dependency


def require_any_permission(*codes: str):
    """Allow administrators, and employees holding at least one of `codes`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_app_permission(c) for c in codes):
            raise ApiError(403, "forbidden", "You do not have permission to perform this action.")
        return user

    return dependency


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for cookie-authenticated, state-changing requests."""
    if request.method in SAFE_METHODS or request.headers.get("authorization"):
        return  # bearer tokens are not sent automatically by browsers
    if not request.cookies.get(ACCESS_COOKIE) and not request.cookies.get(REFRESH_COOKIE):
        return  # not cookie-authenticated; the auth dependency will answer 401
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("x-csrf-token")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise ApiError(403, "csrf_failed", "CSRF validation failed. Refresh the page and try again.")


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
