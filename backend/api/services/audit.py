import json

from accounts.models import AuditLog


def record(user, action: str, entity_type: str, entity_id="", details=None, ip: str | None = None) -> None:
    """Append an audit entry. `details` must never contain passwords or tokens."""
    safe = json.loads(json.dumps(details or {}, default=str))
    AuditLog.objects.create(
        user=user if user is not None and getattr(user, "pk", None) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=safe,
        ip_address=ip,
    )
