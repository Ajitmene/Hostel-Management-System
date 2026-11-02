from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.permissions import ALL_PERMISSIONS, DEFAULT_EMPLOYEE_PERMISSIONS
from common.models import TimeStampedModel
from common.validators import phone_validator


class Role(models.TextChoices):
    ADMIN = "admin", "Administrator"
    EMPLOYEE = "employee", "Employee"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.EMPLOYEE)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["role"] != Role.ADMIN:
            raise ValueError("A superuser must have the admin role.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user that logs in with email and carries the application role."""

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    # Incremented when role, active status or password changes. The API rejects
    # access tokens issued with an older version.
    token_version = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            # Only administrators may ever be staff or superusers.
            models.CheckConstraint(
                condition=Q(role="admin") | Q(is_staff=False, is_superuser=False),
                name="user_only_admin_role_is_staff",
            ),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()

        # Django Admin access is tied to the admin role, never to anything else.
        if self.role == Role.ADMIN:
            self.is_staff = True
        else:
            self.is_staff = False
            self.is_superuser = False

        # Invalidate outstanding tokens when access-relevant fields change.
        if self.pk:
            previous = (
                User.objects.filter(pk=self.pk)
                .values("role", "is_active", "password")
                .first()
            )
            if previous and (
                previous["role"] != self.role
                or previous["is_active"] != self.is_active
                or previous["password"] != self.password
            ):
                self.token_version += 1

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "email", "is_staff", "is_superuser", "token_version",
            }
        super().save(*args, **kwargs)

    def has_app_permission(self, code: str) -> bool:
        """Application-level permission check used by the API."""
        if not self.is_active:
            return False
        if self.role == Role.ADMIN:
            return True
        profile = getattr(self, "employee_profile", None)
        return bool(profile and code in profile.permissions)

    def app_permissions(self) -> list[str]:
        if self.role == Role.ADMIN:
            return list(ALL_PERMISSIONS)
        profile = getattr(self, "employee_profile", None)
        return list(profile.permissions) if profile else []


def default_permissions():
    return list(DEFAULT_EMPLOYEE_PERMISSIONS)


class EmployeeProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee_profile"
    )
    employee_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=16, validators=[phone_validator])
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    joining_date = models.DateField()
    permissions = models.JSONField(default=default_permissions, blank=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.employee_id} - {self.user.email}"

    def clean(self):
        if not isinstance(self.permissions, list):
            raise ValidationError({"permissions": "Permissions must be a list of codes."})
        unknown = set(self.permissions) - set(ALL_PERMISSIONS)
        if unknown:
            raise ValidationError(
                {"permissions": f"Unknown permission codes: {', '.join(sorted(unknown))}"}
            )


class RefreshToken(TimeStampedModel):
    """Server-side record of issued refresh tokens (only a hash is stored)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "revoked_at"])]

    def __str__(self):
        return f"RefreshToken(user={self.user_id}, revoked={self.revoked_at is not None})"


class AuditLog(models.Model):
    """Append-only record of important administrative actions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs",
    )
    action = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}#{self.entity_id}"
