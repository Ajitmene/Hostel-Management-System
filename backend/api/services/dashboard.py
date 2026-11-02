from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.models import AuditLog, EmployeeProfile, Role, User
from accounts.permissions import Permission
from attendance.models import Attendance
from fees.models import Payment, StudentFee
from rooms.models import Room, RoomAllocation
from students.models import Student

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=14, decimal_places=2)


def attendance_today(today) -> dict:
    counts = {r["status"]: r["n"] for r in Attendance.objects.filter(date=today).values("status").annotate(n=Count("id"))}
    active = Student.objects.filter(status=Student.Status.ACTIVE).count()
    marked = sum(counts.values())
    return {
        "present": counts.get("present", 0), "absent": counts.get("absent", 0),
        "leave": counts.get("leave", 0), "unmarked": max(active - marked, 0),
    }


def admin_summary(user: User) -> dict:
    today = timezone.localdate()
    rooms = Room.objects.annotate(occupied=Count("allocations", filter=Q(allocations__is_active=True)))
    open_rooms = [r for r in rooms if r.is_active]
    beds = sum(r.capacity for r in open_rooms)
    occupied_beds = RoomAllocation.objects.filter(is_active=True).count()
    due = StudentFee.objects.aggregate(t=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY))["t"]
    paid = Payment.objects.aggregate(t=Coalesce(Sum("amount"), Value(ZERO), output_field=MONEY))["t"]
    overdue = (
        StudentFee.objects.annotate(paid=Coalesce(Sum("payments__amount"), Value(ZERO), output_field=MONEY))
        .filter(paid__lt=F("amount_due"), due_date__lt=today).count()
    )
    activities = AuditLog.objects.select_related("user")[:10]
    return {
        "role": user.role,
        "total_students": Student.objects.filter(status=Student.Status.ACTIVE).count(),
        "total_employees": EmployeeProfile.objects.filter(user__role=Role.EMPLOYEE, user__is_active=True).count(),
        "total_rooms": len(open_rooms),
        "occupied_rooms": sum(1 for r in open_rooms if r.occupied > 0),
        "available_rooms": sum(1 for r in open_rooms if r.occupied < r.capacity),
        "total_beds": beds,
        "occupied_beds": occupied_beds,
        "pending_fees": due - paid,
        "overdue_fee_count": overdue,
        "attendance_today": attendance_today(today),
        "recent_activities": [
            {"id": a.id, "action": a.action, "entity_type": a.entity_type, "entity_id": a.entity_id,
             "user": a.user.email if a.user else None, "created_at": a.created_at}
            for a in activities
        ],
    }


def employee_summary(user: User) -> dict:
    today = timezone.localdate()
    data = {"role": user.role}
    tasks, links = [], []
    if user.has_app_permission(Permission.STUDENTS_VIEW):
        data["total_students"] = Student.objects.filter(status=Student.Status.ACTIVE).count()
        links.append({"label": "Students", "path": "/employee/students"})
    if user.has_app_permission(Permission.ATTENDANCE_VIEW) or user.has_app_permission(Permission.ATTENDANCE_RECORD):
        att = attendance_today(today)
        data["attendance_today"] = att
        links.append({"label": "Attendance history", "path": "/employee/attendance/history"})
        if user.has_app_permission(Permission.ATTENDANCE_RECORD):
            links.append({"label": "Record attendance", "path": "/employee/attendance"})
            if att["unmarked"]:
                tasks.append(f"Record today's attendance for {att['unmarked']} student(s).")
    if user.has_app_permission(Permission.ROOMS_VIEW):
        data["available_rooms"] = sum(
            1 for r in Room.objects.filter(is_active=True).annotate(o=Count("allocations", filter=Q(allocations__is_active=True)))
            if r.o < r.capacity
        )
        links.append({"label": "Rooms", "path": "/employee/rooms"})
    if user.has_app_permission(Permission.FEES_VIEW):
        links.append({"label": "Fees", "path": "/employee/fees"})
    data["tasks"] = tasks
    data["quick_links"] = links
    return data
