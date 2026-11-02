"""Login, refresh-token rotation and logout."""
from datetime import timedelta

from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import RefreshToken, User
from api.core.config import get_settings
from api.core.errors import ApiError
from api.core.security import create_access_token, hash_token, new_csrf_token, new_refresh_token
from api.services import audit
from api.services.employees import revoke_refresh_tokens

INVALID_CREDENTIALS = ApiError(401, "invalid_credentials", "Incorrect email or password.")


def serialize_user(user: User) -> dict:
    profile = getattr(user, "employee_profile", None)
    return {
        "id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name,
        "role": user.role, "permissions": user.app_permissions(),
        "employee_id": profile.employee_id if profile else None,
    }


def authenticate_user(email: str, password: str, ip=None) -> User:
    user = authenticate(username=email.strip().lower(), password=password)
    if user is None:
        # Same message whether the email exists or not, so accounts cannot be enumerated.
        audit.record(None, "auth.login_failed", "user", "", {"email": email.strip().lower()[:254]}, ip)
        raise ApiError(401, "invalid_credentials", "Incorrect email or password.")
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return user


def issue_tokens(user: User) -> dict:
    """Create an access JWT, a stored (hashed) refresh token and a CSRF token."""
    s = get_settings()
    access, seconds = create_access_token(user)
    raw_refresh, refresh_hash = new_refresh_token()
    RefreshToken.objects.create(
        user=user, token_hash=refresh_hash, expires_at=timezone.now() + timedelta(days=s.refresh_token_days)
    )
    return {"access": access, "access_seconds": seconds, "refresh": raw_refresh, "csrf": new_csrf_token()}


def rotate_refresh_token(raw: str | None) -> tuple[User, dict]:
    if not raw:
        raise ApiError(401, "not_authenticated", "Authentication required.")
    reused_by: User | None = None
    with transaction.atomic():
        token = RefreshToken.objects.select_for_update().select_related("user").filter(token_hash=hash_token(raw)).first()
        if token is None:
            raise ApiError(401, "invalid_token", "Invalid refresh token.")
        if token.revoked_at is not None:
            reused_by = token.user
        else:
            if token.expires_at <= timezone.now():
                raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.")
            if not token.user.is_active:
                raise ApiError(401, "account_inactive", "This account has been deactivated.")
            token.revoked_at = timezone.now()
            token.save(update_fields=["revoked_at", "updated_at"])
            user = User.objects.select_related("employee_profile").get(pk=token.user_id)
            return user, issue_tokens(user)
    # A used token came back: assume theft and sign this user out everywhere.
    # Done outside the transaction above so the revocation is not rolled back.
    revoke_refresh_tokens(reused_by)
    audit.record(reused_by, "auth.refresh_reuse_detected", "user", reused_by.id, {})
    raise ApiError(401, "token_revoked", "Your session is no longer valid. Please sign in again.")


def revoke_presented_token(raw: str | None) -> User | None:
    """Revoke the refresh token from the cookie and return its owner, if known."""
    if not raw:
        return None
    token = RefreshToken.objects.select_related("user").filter(token_hash=hash_token(raw)).first()
    if token and token.revoked_at is None:
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at", "updated_at"])
    return token.user if token else None


def change_password(user: User, current: str, new: str, ip=None) -> dict:
    if not user.check_password(current):
        raise ApiError(400, "wrong_password", "Your current password is incorrect.")
    try:
        password_validation.validate_password(new, user=user)
    except DjangoValidationError as exc:
        raise ApiError(422, "weak_password", "The new password is not strong enough.",
                       [{"field": "new_password", "message": m} for m in exc.messages])
    with transaction.atomic():
        user.set_password(new)
        user.save()  # bumps token_version: every other session is signed out
        revoke_refresh_tokens(user)
        audit.record(user, "auth.change_password", "user", user.id, {}, ip)
        return issue_tokens(user)
