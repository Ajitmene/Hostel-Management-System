from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import EmployeeProfile, RefreshToken, Role, User
from accounts.permissions import ALL_PERMISSIONS
from api.core.errors import ApiError
from api.services import audit


def employee_queryset():
    return EmployeeProfile.objects.select_related("user").filter(user__role=Role.EMPLOYEE)


def serialize_employee(p: EmployeeProfile) -> dict:
    u = p.user
    return {
        "id": p.id, "user_id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email,
        "employee_id": p.employee_id, "phone": p.phone, "designation": p.designation, "department": p.department,
        "joining_date": p.joining_date, "permissions": p.permissions, "is_active": u.is_active, "role": u.role,
    }


def get_employee_or_404(employee_id: int) -> EmployeeProfile:
    p = employee_queryset().filter(pk=employee_id).first()
    if not p:
        raise ApiError(404, "not_found", "Employee not found.")
    return p


def validate_new_password(password: str, user: User | None = None) -> None:
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ApiError(422, "weak_password", "The password is not strong enough.",
                       [{"field": "password", "message": m} for m in exc.messages])


def _clean_permissions(perms: list[str]) -> list[str]:
    unknown = sorted(set(perms) - set(ALL_PERMISSIONS))
    if unknown:
        raise ApiError(422, "invalid_permissions", f"Unknown permission codes: {', '.join(unknown)}.",
                       [{"field": "permissions", "message": f"Allowed: {', '.join(ALL_PERMISSIONS)}"}])
    return sorted(set(perms), key=ALL_PERMISSIONS.index)


def _check_unique(email: str, employee_id: str, exclude_user_id=None, exclude_profile_id=None):
    problems = []
    users = User.objects.filter(email__iexact=email)
    profiles = EmployeeProfile.objects.filter(employee_id__iexact=employee_id)
    if exclude_user_id:
        users = users.exclude(pk=exclude_user_id)
    if exclude_profile_id:
        profiles = profiles.exclude(pk=exclude_profile_id)
    if users.exists():
        problems.append({"field": "email", "message": "This email is already in use."})
    if profiles.exists():
        problems.append({"field": "employee_id", "message": "This employee ID is already in use."})
    if problems:
        raise ApiError(409, "duplicate", "An employee with these details already exists.", problems)


def revoke_refresh_tokens(user: User) -> None:
    RefreshToken.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())


def create_employee(data: dict, actor, ip=None) -> EmployeeProfile:
    perms = _clean_permissions(data["permissions"])
    _check_unique(data["email"], data["employee_id"])
    candidate = User(email=data["email"], first_name=data["first_name"], last_name=data["last_name"])
    validate_new_password(data["password"], candidate)
    try:
        with transaction.atomic():
            # Role is forced server-side: this endpoint can only ever create employees.
            user = User.objects.create_user(
                email=data["email"], password=data["password"],
                first_name=data["first_name"], last_name=data["last_name"], role=Role.EMPLOYEE,
            )
            profile = EmployeeProfile.objects.create(
                user=user, employee_id=data["employee_id"], phone=data["phone"], designation=data["designation"],
                department=data["department"], joining_date=data["joining_date"], permissions=perms,
            )
            audit.record(actor, "employee.create", "employee", profile.id,
                         {"email": user.email, "employee_id": profile.employee_id, "permissions": perms}, ip)
    except IntegrityError:
        raise ApiError(409, "duplicate", "An employee with these details already exists.")
    return get_employee_or_404(profile.id)


def update_employee(employee_id: int, data: dict, actor, ip=None) -> EmployeeProfile:
    profile = get_employee_or_404(employee_id)
    perms = _clean_permissions(data["permissions"])
    _check_unique(data["email"], data["employee_id"], profile.user_id, profile.id)
    with transaction.atomic():
        user = profile.user
        user.email, user.first_name, user.last_name = data["email"], data["first_name"], data["last_name"]
        user.save()
        for field in ("employee_id", "phone", "designation", "department", "joining_date"):
            setattr(profile, field, data[field])
        profile.permissions = perms
        profile.save()
        audit.record(actor, "employee.update", "employee", profile.id, {"permissions": perms}, ip)
    return get_employee_or_404(employee_id)


def set_active(employee_id: int, is_active: bool, actor, ip=None) -> EmployeeProfile:
    profile = get_employee_or_404(employee_id)
    with transaction.atomic():
        user = profile.user
        user.is_active = is_active
        user.save()  # bumps token_version, instantly invalidating access tokens
        if not is_active:
            revoke_refresh_tokens(user)
        audit.record(actor, "employee.activate" if is_active else "employee.deactivate", "employee", profile.id, {}, ip)
    return get_employee_or_404(employee_id)


def reset_password(employee_id: int, new_password: str, actor, ip=None) -> None:
    profile = get_employee_or_404(employee_id)
    validate_new_password(new_password, profile.user)
    with transaction.atomic():
        profile.user.set_password(new_password)
        profile.user.save()
        revoke_refresh_tokens(profile.user)
        audit.record(actor, "employee.reset_password", "employee", profile.id, {}, ip)
